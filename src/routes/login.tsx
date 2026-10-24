import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { zodValidator, fallback } from "@tanstack/zod-adapter";
import { z } from "zod";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { actions } from "@/lib/library/store";
import { firebaseConfigured, firebaseSignIn } from "@/lib/firebase";

export const Route = createFileRoute("/login")({
  validateSearch: zodValidator(z.object({ mode: fallback(z.string(), "signin").default("signin") })),
  head: () => ({
    meta: [
      { title: "Sign in — UniLibrary" },
      { name: "description", content: "Sign in or register for your UniLibrary account." },
      { property: "og:title", content: "Sign in — UniLibrary" },
      { property: "og:description", content: "Access your university library account." },
    ],
  }),
  component: Login,
});

const signInSchema = z.object({ email: z.string().trim().email("Enter a valid email").max(255), password: z.string().min(6, "At least 6 characters").max(128) });
const regSchema = signInSchema.extend({
  name: z.string().trim().min(2, "Enter your name").max(100),
  roll: z.string().trim().regex(/^[A-Za-z0-9]{4,15}$/, "Roll number: 4–15 letters/digits"),
  dept: z.string().trim().min(2).max(60),
});

const DEMO = [
  ["Student", "student@unilibrary.edu"],
  ["Librarian", "librarian@unilibrary.edu"],
  ["Admin", "admin@unilibrary.edu"],
  ["Faculty", "faculty@unilibrary.edu"],
];

function Login() {
  const { mode } = Route.useSearch();
  const navigate = useNavigate();
  const [tab, setTab] = useState(mode === "register" ? "register" : "signin");
  const [f, setF] = useState({ email: "", password: "", name: "", roll: "", dept: "Computer Science" });
  const [busy, setBusy] = useState(false);
  const up = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  const done = (role: string) => navigate({ to: role === "librarian" ? "/librarian" : role === "admin" ? "/admin" : "/my-library" });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = tab === "register" ? regSchema.safeParse(f) : signInSchema.safeParse(f);
    if (!parsed.success) return toast.error(parsed.error.issues[0].message);
    setBusy(true);
    try {
      if (firebaseConfigured) {
        const r = await firebaseSignIn(f.email, f.password, tab === "register" ? { name: f.name } : undefined);
        actions.signInExternal(r.uid, r.email, r.name, r.role);
        done(r.role);
      } else if (tab === "register") {
        actions.register(f.name.trim(), f.email.trim(), f.roll.trim().toUpperCase(), f.dept.trim());
        toast.success("Account created (demo mode)");
        done("student");
      } else {
        const u = actions.signInDemo(f.email.trim());
        done(u.role);
      }
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-4xl gap-6 py-4 md:grid-cols-2">
      <div className="rounded-2xl bg-navy p-6 text-navy-foreground sm:p-8">
        <h1 className="text-2xl font-extrabold">Welcome to UniLibrary</h1>
        <p className="mt-2 text-sm opacity-80">Search the catalog, reserve books, track due dates and fines — all in one place.</p>
        {!firebaseConfigured && (
          <div className="mt-6 rounded-xl bg-sidebar-accent p-4">
            <p className="text-sm font-bold">Demo mode</p>
            <p className="mt-1 text-xs opacity-80">Firebase isn't configured yet, so data is saved in this browser. Try a demo account (any password):</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {DEMO.map(([r, em]) => (
                <button key={r} onClick={() => done(actions.signInDemo(em).role)} className="rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-accent-foreground">{r}</button>
              ))}
            </div>
          </div>
        )}
      </div>
      <form onSubmit={submit} className="flex flex-col gap-4 rounded-2xl border bg-card p-6 shadow-card sm:p-8">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full"><TabsTrigger value="signin" className="flex-1">Sign in</TabsTrigger><TabsTrigger value="register" className="flex-1">Register</TabsTrigger></TabsList>
        </Tabs>
        {tab === "register" && (
          <>
            <div className="grid gap-1.5"><Label htmlFor="name">Full name</Label><Input id="name" value={f.name} onChange={up("name")} maxLength={100} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1.5"><Label htmlFor="roll">Roll number</Label><Input id="roll" value={f.roll} onChange={up("roll")} maxLength={15} /></div>
              <div className="grid gap-1.5"><Label htmlFor="dept">Department</Label><Input id="dept" value={f.dept} onChange={up("dept")} maxLength={60} /></div>
            </div>
          </>
        )}
        <div className="grid gap-1.5"><Label htmlFor="email">University email</Label><Input id="email" type="email" value={f.email} onChange={up("email")} maxLength={255} /></div>
        <div className="grid gap-1.5"><Label htmlFor="pw">Password</Label><Input id="pw" type="password" value={f.password} onChange={up("password")} maxLength={128} /></div>
        <Button type="submit" disabled={busy} size="lg">{tab === "register" ? "Create student account" : "Sign in"}</Button>
        <p className="text-xs text-muted-foreground">New accounts are always students. Librarian and admin access is granted by an administrator.</p>
      </form>
    </div>
  );
}
