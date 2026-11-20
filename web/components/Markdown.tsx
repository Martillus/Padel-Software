import { Fragment, type ReactNode } from "react";

/** Markdown muy sencillo (negrita, cursiva, listas, citas, títulos) sin insertar HTML. */
function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|(?<![\w])_[^_]+_(?![\w]))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    out.push(tok.startsWith("**") ? <strong key={`${keyBase}-${i++}`}>{tok.slice(2, -2)}</strong> : <em key={`${keyBase}-${i++}`}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text, className = "" }: { text: string; className?: string }) {
  const blocks: ReactNode[] = [];
  let list: string[] = [];
  const flush = (k: number) => {
    if (!list.length) return;
    blocks.push(
      <ul key={`ul-${k}`} className="my-2 list-disc space-y-1 pl-5">
        {list.map((li, j) => (
          <li key={j}>{inline(li, `li-${k}-${j}`)}</li>
        ))}
      </ul>,
    );
    list = [];
  };
  text.split("\n").forEach((raw, k) => {
    const line = raw.trimEnd();
    const item = /^\s*[-*] (.*)/.exec(line);
    if (item) {
      list.push(item[1]);
      return;
    }
    flush(k);
    if (!line.trim()) return;
    if (line.startsWith("#")) {
      const t = line.replace(/^#+\s*/, "");
      blocks.push(<h4 key={k} className="mt-4 mb-1 font-bold text-ink">{inline(t, `h-${k}`)}</h4>);
    } else if (line.startsWith("> ")) {
      blocks.push(<p key={k} className="my-2 rounded-xl bg-amber-400/10 px-3 py-2 text-sm text-amber-200">{inline(line.slice(2), `q-${k}`)}</p>);
    } else {
      blocks.push(<p key={k} className="my-2">{inline(line, `p-${k}`)}</p>);
    }
  });
  flush(-1);
  return <div className={className}>{blocks.map((b, i) => <Fragment key={i}>{b}</Fragment>)}</div>;
}

/** Separa el informe del motor en apartados por título "## ...". */
export function splitSections(md: string): Record<string, string> {
  const out: Record<string, string> = {};
  let current = "_intro";
  for (const line of md.split("\n")) {
    if (line.startsWith("## ")) {
      current = line.slice(3).trim();
      out[current] = "";
    } else if (!line.startsWith("# ")) {
      out[current] = (out[current] ?? "") + line + "\n";
    }
  }
  return out;
}
