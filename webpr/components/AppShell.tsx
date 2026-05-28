import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import styles from "./AppShell.module.css";

type AppShellProps = {
  children: React.ReactNode;
  active?: string;
  searchPlaceholder?: string;
  userName?: string;
  role?: string;
};

export default function AppShell({
  children,
  searchPlaceholder = "Tìm kiếm...",
  userName = "Admin User",
  role = "Super Administrator",
}: AppShellProps) {
  return (
    <div className={styles.shell}>
      <Sidebar />

      <main className={styles.main}>
        <Topbar
          placeholder={searchPlaceholder}
          userName={userName}
          role={role}
        />

        <div className={styles.content}>{children}</div>
      </main>
    </div>
  );
}
