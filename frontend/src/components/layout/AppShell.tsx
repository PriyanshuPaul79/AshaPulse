import { Outlet, NavLink, useLocation } from "react-router-dom";
import { PlusCircle, ClipboardList, MapPin, Search } from "lucide-react";
import { cn } from "../../lib/utils";

export default function AppShell() {
  const location = useLocation();

  const navItems = [
    { to: "/", icon: PlusCircle, label: "Home", hindiLabel: "Ghar" },
    { to: "/history", icon: ClipboardList, label: "History", hindiLabel: "Itihas" },
    { to: "/phc", icon: MapPin, label: "PHC", hindiLabel: "Kendra" }
  ];

  return (
    <div className="flex flex-col min-h-[100dvh] bg-background max-w-md mx-auto relative shadow-2xl overflow-hidden">
      <main className="flex-1 overflow-y-auto pb-20">
        <Outlet />
      </main>
      
      {/* Bottom Nav */}
      <nav className="fixed bottom-0 w-full max-w-md mx-auto h-[64px] bg-surface-elevated border-t border-border flex items-center justify-around z-50">
        {navItems.map((item) => {
          const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to));
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                "flex flex-col items-center justify-center w-full h-full text-text-muted transition-colors duration-200",
                isActive && "text-success"
              )}
            >
              <item.icon className="w-6 h-6 mb-1" strokeWidth={isActive ? 2.5 : 2} fill={isActive ? "currentColor" : "none"} viewBox={isActive ? "0 0 24 24" : "0 0 24 24"} />
              <span className="text-[10px] font-medium leading-none">{isActive ? item.label : item.hindiLabel}</span>
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}
