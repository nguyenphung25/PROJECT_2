import { Bell, Search, Settings } from 'lucide-react';
import styles from './Topbar.module.css';

export default function Topbar({ placeholder, userName, role }: { placeholder: string; userName: string; role: string }) {
  return (
    <header className={styles.topbar}>
      <div className={styles.searchBox}>
        <Search size={21} />
        <input placeholder={placeholder} />
      </div>
      <div className={styles.actions}>
        <Bell size={21} />
        <Settings size={23} />
        <div className={styles.divider} />
        <div className={styles.userText}>
          <strong>{userName}</strong>
          <span>{role}</span>
        </div>
        <div className={styles.avatar}>A</div>
      </div>
    </header>
  );
}
