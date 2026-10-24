import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge, fmtDate } from "@/components/lib/bits";
import { actions, useLibrary } from "@/lib/library/store";
import { checkIssueEligibility, dueBadge } from "@/lib/library/rules";

export const Route = createFileRoute("/librarian")({
  head: () => ({
    meta: [
      { title: "Circulation Desk — UniLibrary" },
      { name: "description", content: "Issue and return books, manage inventory and overdue loans." },
      { property: "og:title", content: "Circulation Desk — UniLibrary" },
      { property: "og:description", content: "Librarian circulation workflows." },
    ],
  }),
  component: Desk,
});

function Desk() {
  const { state, user } = useLibrary();
  const [roll, setRoll] = useState("");
  const [bc, setBc] = useState("");
  const [days, setDays] = useState(state.settings.loanDays);
  const [rbc, setRbc] = useState("");
  const [nb, setNb] = useState({ title: "", author: "", category: "Computer Science", year: 2024, isbn13: "", publisher: "", copies: 2, shelf: "Floor 1, Shelf A-1" });
  if (!user || (user.role !== "librarian" && user.role !== "admin")) return <p className="py-16 text-center font-semibold">Librarian access only.</p>;
  const student = state.users.find((u) => u.rollNumber?.toLowerCase() === roll.trim().toLowerCase() || u.email === roll.trim());
  const el = student && checkIssueEligibility(state, student);
  const active = state.loans.filter((l) => l.status === "active");
  const title = (id: string) => state.books.find((b) => b.id === id)?.title;
  const run = (fn: () => void) => { try { fn(); } catch (e) { toast.error((e as Error).message); } };

  return (
    <div className="mx-auto grid max-w-6xl gap-5">
      <h1 className="text-2xl font-extrabold text-navy">Circulation Desk</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border bg-card p-4 shadow-card">
          <h2 className="font-bold">Fast Issue</h2>
          <Input className="mt-3" placeholder="Student roll no. (e.g. CSE21B012)" value={roll} onChange={(e) => setRoll(e.target.value)} />
          {student && <p className="mt-2 text-sm">{student.name} — {el?.ok ? <StatusBadge tone="success">Eligible</StatusBadge> : <StatusBadge tone="destructive">{el && !el.ok && el.reason}</StatusBadge>}</p>}
          <Input className="mt-3" placeholder="Copy barcode (e.g. UL1011)" value={bc} onChange={(e) => setBc(e.target.value)} />
          <label className="mt-3 flex items-center gap-2 text-sm">Loan days <Input type="number" min={1} max={60} className="w-20" value={days} onChange={(e) => setDays(Number(e.target.value))} /></label>
          <Button className="mt-3 w-full" disabled={!student} onClick={() => run(() => { actions.issue(student!.id, bc.trim(), days); toast.success("Book issued"); setBc(""); })}>Confirm issue</Button>
        </section>
        <section className="rounded-xl border bg-card p-4 shadow-card">
          <h2 className="font-bold">Fast Return</h2>
          <Input className="mt-3" placeholder="Copy barcode" value={rbc} onChange={(e) => setRbc(e.target.value)} />
          <div className="mt-3 flex gap-2">
            {[false, true].map((pay) => <Button key={String(pay)} variant={pay ? "outline" : "default"} className="flex-1" onClick={() => run(() => { const r = actions.returnCopy(rbc.trim(), pay); toast.success(r.amount ? `Returned ${r.late}d late — fine ₹${r.amount}${pay ? " paid" : " added to dues"}` : "Returned on time"); if (r.heldFor) toast.info("Copy held for next student in queue"); setRbc(""); })}>{pay ? "Return + fine paid" : "Return"}</Button>)}
          </div>
        </section>
      </div>
      <section className="rounded-xl border bg-card p-4 shadow-card">
        <h2 className="font-bold">Active loans ({active.length})</h2>
        <div className="mt-2 grid gap-2">
          {active.map((l) => { const d = dueBadge(l.dueDate, new Date()); const u = state.users.find((x) => x.id === l.userId); const c = state.copies.find((x) => x.id === l.copyId);
            return <div key={l.id} className="flex flex-wrap items-center justify-between gap-2 border-b pb-2 text-sm"><span className="min-w-0 truncate"><b>{title(l.bookId)}</b> · {c?.barcode} · {u?.rollNumber ?? u?.name}</span><span className="flex items-center gap-2 text-xs">Due {fmtDate(l.dueDate)} <StatusBadge tone={d.tone}>{d.label}</StatusBadge></span></div>; })}
        </div>
      </section>
      <section className="rounded-xl border bg-card p-4 shadow-card">
        <h2 className="font-bold">Add new book</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {(["title", "author", "category", "publisher", "isbn13", "shelf"] as const).map((k) => <Input key={k} placeholder={k} value={nb[k]} maxLength={150} onChange={(e) => setNb({ ...nb, [k]: e.target.value })} />)}
          <Input type="number" placeholder="Year" value={nb.year} onChange={(e) => setNb({ ...nb, year: Number(e.target.value) })} />
          <Input type="number" min={1} max={50} placeholder="Copies" value={nb.copies} onChange={(e) => setNb({ ...nb, copies: Number(e.target.value) })} />
        </div>
        <Button className="mt-3" onClick={() => run(() => { if (!nb.title.trim() || !nb.author.trim() || !/^\d{13}$/.test(nb.isbn13)) throw new Error("Title, author and a 13-digit ISBN are required"); actions.addBook(nb); toast.success("Book added with copies"); })}>Add book</Button>
      </section>
    </div>
  );
}
