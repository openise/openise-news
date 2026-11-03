import { z } from "zod";
import { WIKI_TYPES } from "../constants/wiki.ts";
import { parseSourceReference } from "../domain/source-reference.ts";

const dateString = z
  .string()
  .regex(/^\d{14}$/, "日時は YYYYMMDDHHmmss 形式の 14 桁で指定してください");

const sourceReferenceString = z.string().refine(
  (value) => {
    try {
      parseSourceReference(value);
      return true;
    } catch {
      return false;
    }
  },
  { message: "sources には Clip・Source・full Wiki path の local 参照だけを指定できます" },
);

export const clipSchema = z.object({
  title: z.string(),
  createdDate: dateString,
  updatedDate: dateString.optional(),
  url: z.url(),
  description: z.string(),
  tags: z.array(z.string()),
  pinned: z.boolean(),
});

export const wikiSchema = z.object({
  title: z.string(),
  createdDate: dateString,
  updatedDate: dateString.optional(),
  description: z.string(),
  tags: z.array(z.string()),
  type: z.enum(WIKI_TYPES),
  sources: z.array(sourceReferenceString).optional(),
  graphExclude: z.boolean().optional(),
});

export const sourceSchema = z.looseObject({
  sourceProject: z.string(),
  sourcePath: z.string(),
  sourceCommit: z.string(),
  importedDate: dateString,
  sourceFormat: z.enum(["markdown", "text"]),
  sourceLanguage: z.string(),
});

export const newsSchema = z.object({
  title: z.string().min(1),
  createdDate: dateString,
  description: z.string().min(1),
});
