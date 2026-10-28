import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/lib/bits";
import { actions, useLibrary } from "@/lib/library/store";

export const Route = createFileRoute("/resources")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Digital Resources — UniLibrary" },
      { name: "description", content: "Lecture notes, past exam papers and syllabus copies." },
      { property: "og:title", content: "Digital Resources — UniLibrary" },
      { property: "og:description", content: "Approved digital learning resources." },
    ],
  }),
  component: Resources,
});

function Resources() {
  const { state, user } = useLibrary();
  const [t, setT] = useState("");
  const [c, setC] = useState("");
  const staff = user && user.role !== "student";
  const list = state.resources.filter((r) => r.approved || user?.role === "admin");
  return (
    <div className="mx-auto grid max-w-5xl gap-5">
      <h1 className="text-2xl font-extrabold text-navy">Digital Learning Resources</h1>
      <div className="grid gap-3 sm:grid-cols-2">
        {list.map((r) => (
          <div key={r.id} className="flex items-center gap-3 rounded-xl border bg-card p-4 shadow-card">
            <FileText className="size-8 shrink-0 text-teal" />
            <div className="min-w-0 flex-1"><p className="truncate font-semibold">{r.title}</p><p className="text-xs text-muted-foreground">{r.kind} · {r.course}</p></div>
            {r.approved ? <StatusBadge tone="success">Approved</StatusBadge> : <Button size="sm" onClick={() => { actions.approveResource(r.id); toast.success("Approved"); }}>Approve</Button>}
          </div>
        ))}
      </div>
      {staff && (
        <form className="flex flex-wrap gap-2 rounded-xl border bg-card p-4" onSubmit={(e) => { e.preventDefault(); if (t.trim().length < 3) return toast.error("Enter a title"); try { actions.submitResource(t.trim(), "Lecture Notes", c.trim() || "General"); setT(""); toast.success("Submitted for approval"); } catch (er) { toast.error((er as Error).message); } }}>
          <Input className="min-w-0 flex-1" placeholder="Resource title" value={t} maxLength={120} onChange={(e) => setT(e.target.value)} />
          <Input className="w-28" placeholder="Course" value={c} maxLength={20} onChange={(e) => setC(e.target.value)} />
          <Button type="submit">Submit</Button>
        </form>
      )}
    </div>
  );
}
