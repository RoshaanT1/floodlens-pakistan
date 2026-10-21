import { Link, NavLink } from "react-router-dom";
import { Moon, Sun, Waves } from "lucide-react";
import { LIVE_LABEL } from "@/data/mockData";
import { useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Situation Room", end: true },
  { to: "/food-prices", label: "Food Prices", end: false },
  { to: "/live", label: "Live data", end: false },
  { to: "/ask", label: "Ask", end: false },
  { to: "/sources", label: "Sources & Methods", end: false },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "rounded px-2.5 py-1.5 text-sm transition-colors",
    isActive
      ? "bg-accent text-foreground"
      : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
  );

export default function TopBar() {
  const { theme, toggle } = useTheme();

  return (
    <header className="z-30 shrink-0 border-b border-border bg-card/70 backdrop-blur">
      <div className="flex h-12 items-center gap-3 px-3">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded bg-primary text-primary-foreground">
            <Waves className="h-4 w-4" />
          </span>
          <span className="font-heading text-sm font-semibold tracking-tight">FloodLens</span>
        </Link>

        <span className="hidden items-center gap-1.5 rounded border border-border bg-background/60 px-2 py-[3px] text-xs text-muted-foreground sm:inline-flex">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
          {LIVE_LABEL}
        </span>

        <nav className="ml-auto hidden items-center gap-0.5 md:flex">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <button
          type="button"
          onClick={toggle}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          className="ml-auto flex h-7 w-7 shrink-0 items-center justify-center rounded border border-border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:ml-2"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex items-center gap-0.5 overflow-x-auto border-t border-border/60 px-3 py-1 md:hidden">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={cn(linkClass, "shrink-0 py-1 text-xs")}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}