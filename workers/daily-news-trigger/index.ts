interface Env {
  GITHUB_ACTIONS_TOKEN: string;
}

export default {
  async scheduled(_controller: unknown, env: Env): Promise<void> {
    if (!env.GITHUB_ACTIONS_TOKEN?.trim()) {
      const message = "Daily News の起動に失敗しました: GITHUB_ACTIONS_TOKEN が未設定です";
      console.error(message);
      throw new Error(message);
    }

    let response: Response;
    try {
      response = await fetch(
        "https://api.github.com/repos/openise/openise-news/actions/workflows/daily-news.yml/dispatches",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${env.GITHUB_ACTIONS_TOKEN}`,
            Accept: "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "openise-news-trigger",
            "X-GitHub-Api-Version": "2022-11-28",
          },
          body: JSON.stringify({ ref: "main", inputs: { force: false } }),
          signal: AbortSignal.timeout(10_000),
          redirect: "error",
        },
      );
    } catch {
      // 通信例外にはリクエスト情報が含まれうるため、そのままログや例外に渡さない。
      const message = "Daily News の起動に失敗しました: GitHub API への通信失敗またはタイムアウト";
      console.error(message);
      throw new Error(message);
    }

    if (response.status !== 204) {
      const message = `Daily News の起動に失敗しました: GitHub API が HTTP ${response.status} を返しました`;
      console.error(message);
      throw new Error(message);
    }

    console.log("Daily News の起動リクエストが受理されました（main、force=false）");
  },
};
