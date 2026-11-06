import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import worker from "./index";

describe("Daily News の定期起動", () => {
  const token = "test-secret-token";
  const env = { GITHUB_ACTIONS_TOKEN: token };
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("main の Daily News を force=false で起動し、受理を記録する", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await worker.scheduled({}, env);

    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      "https://api.github.com/repos/openise/openise-news/actions/workflows/daily-news.yml/dispatches",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
          "User-Agent": "openise-news-trigger",
          "X-GitHub-Api-Version": "2022-11-28",
        }),
        body: JSON.stringify({ ref: "main", inputs: { force: false } }),
        signal: expect.any(AbortSignal),
        redirect: "error",
      }),
    );
    expect(console.log).toHaveBeenCalledWith(expect.stringContaining("受理"));
    expect(console.error).not.toHaveBeenCalled();
    expect(JSON.stringify(vi.mocked(console.log).mock.calls)).not.toContain(token);
  });

  it.each([401, 403, 404, 422, 429, 500])("HTTP %i を失敗として記録し、応答本文を漏らさない", async (status) => {
    fetchMock.mockResolvedValue(new Response(`応答本文 ${token}`, { status }));

    await expect(worker.scheduled({}, env)).rejects.toThrow(`HTTP ${status}`);

    expect(console.error).toHaveBeenCalledWith(expect.stringContaining(`HTTP ${status}`));
    expect(JSON.stringify(vi.mocked(console.error).mock.calls)).not.toContain(token);
    expect(console.log).not.toHaveBeenCalled();
  });

  it.each([
    new Error(`通信失敗 ${token}`),
    new DOMException(`タイムアウト ${token}`, "TimeoutError"),
  ])("通信失敗をログと例外に記録し、元の例外に含まれる秘密を漏らさない", async (error) => {
    fetchMock.mockRejectedValue(error);

    await expect(worker.scheduled({}, env)).rejects.toThrow(
      /^Daily News の起動に失敗しました: GitHub API への通信失敗またはタイムアウト$/,
    );
    expect(console.error).toHaveBeenCalled();
    expect(JSON.stringify(vi.mocked(console.error).mock.calls)).not.toContain(token);
    expect(console.log).not.toHaveBeenCalled();
  });

  it.each([undefined, "", " "])("secret が未設定なら API を呼ばずに失敗する", async (value) => {
    // Env の型を緩めず、実行時に secret が欠損する場合も再現する。
    await expect(worker.scheduled({}, { GITHUB_ACTIONS_TOKEN: value! })).rejects.toThrow("未設定");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(console.error).toHaveBeenCalledWith(expect.stringContaining("未設定"));
  });
});
