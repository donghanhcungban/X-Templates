// Kiểm ngoại lệ quét phụ thuộc (BASE-DEP-004): mỗi GHSA/CVE bị `pnpm audit` bỏ qua (`auditConfig.ignoreGhsas`/
// `ignoreCves` của pnpm-workspace.yaml) phải có dòng trong audit-exceptions.json còn hạn, đủ khoá; mỗi dòng ngoại lệ
// phải đang được bỏ qua. Dạng danh sách không đọc chắc được → đỏ. Chạy: `pnpm audit:exceptions` (exit 1 khi sai).
import { readFileSync } from "node:fs";

const KEYS = ["ghsa", "cve", "package", "reason", "owner", "approved_by", "expires"];

type Exception = Record<string, string | null>;

function unquote(s: string): string {
  return s.trim().replace(/^["']|["']$/g, "");
}

export function ignoredIds(text: string, key: string): string[] {
  const out: string[] = [];
  let inList = false;
  for (const line of text.split("\n")) {
    if (!line.trim() || line.trim().startsWith("#")) {
      continue;
    }
    const head = line.match(new RegExp(`^\\s+${key}:\\s*(.*?)\\s*(#.*)?$`));
    if (head) {
      const rest = head[1] ?? "";
      inList = rest === "";
      if (rest === "" || rest === "[]") {
        continue;
      }
      const flow = rest.match(/^\[([^\]]*)\]$/);
      if (!flow) {
        throw new Error(`không đọc được ${key}: ${rest}`);
      }
      out.push(...(flow[1] ?? "").split(",").map(unquote));
      continue;
    }
    const item = line.match(/^\s+-\s+(\S+)\s*(#.*)?$/);
    if (inList && item) {
      out.push(unquote(item[1] ?? ""));
    } else {
      inList = false;
    }
  }
  return out;
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const REQUIRED_TEXT = ["reason", "approved_by", "owner"];

export function problems(workspace: string, exceptions: Exception[], today: string): string[] {
  const errs: string[] = [];
  if (/^\s*auditConfig:\s*\{/m.test(workspace)) {
    // dạng flow-mapping (`auditConfig: { ignoreGhsas: [...] }`) không đọc chắc → đỏ, không bỏ qua im lặng
    errs.push("auditConfig dạng flow-mapping `{ … }`: viết dạng khối để kiểm được");
  }
  const ghsas = ignoredIds(workspace, "ignoreGhsas");
  const cves = ignoredIds(workspace, "ignoreCves");
  for (const e of exceptions) {
    const id = e.ghsa ?? e.cve ?? "?";
    const missing = KEYS.filter((k) => !(k in e));
    if (missing.length > 0) {
      errs.push(`${id}: thiếu khoá ${missing.join(", ")}`);
    }
    // `null`, "never", ngày sai dạng: không phải hạn — so chuỗi với hôm nay sẽ cho qua ("never" > "2026-…")
    if (typeof e.expires !== "string" || !DATE_RE.test(e.expires)) {
      errs.push(`${id}: expires phải là YYYY-MM-DD, có ${String(e.expires)}`);
    } else if (e.expires < today) {
      errs.push(`${id}: hết hạn ${e.expires}`);
    }
    for (const k of REQUIRED_TEXT) {
      if (k in e && (typeof e[k] !== "string" || String(e[k]).trim() === "")) {
        errs.push(`${id}: ${k} rỗng`);
      }
    }
    const used = (e.ghsa != null && ghsas.includes(e.ghsa)) || (e.cve != null && cves.includes(e.cve));
    if (!used) {
      errs.push(`${id}: ngoại lệ không còn được bỏ qua`);
    }
  }
  const orphans = [
    ...ghsas.filter((g) => !exceptions.some((e) => e.ghsa === g)),
    ...cves.filter((c) => !exceptions.some((e) => e.cve === c)),
  ];
  for (const o of orphans) {
    errs.push(`${o}: bỏ qua mà không có ngoại lệ`);
  }
  return errs;
}

if (import.meta.main) {
  const workspace = readFileSync("pnpm-workspace.yaml", "utf8");
  const data = JSON.parse(readFileSync("audit-exceptions.json", "utf8")) as { exceptions: Exception[] };
  const errs = problems(workspace, data.exceptions, new Date().toISOString().slice(0, 10));
  for (const e of errs) {
    console.error(e);
  }
  process.exit(errs.length > 0 ? 1 : 0);
}
