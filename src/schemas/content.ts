import { z } from "astro/zod";

const dateString = z
  .string()
  .regex(/^\d{14}$/, "日時は YYYYMMDDHHmmss 形式の 14 桁で指定してください");

export const newsSchema = z.object({
  title: z.string().min(1),
  createdDate: dateString,
});
