import styles from './StatusBadge.module.css';

export default function StatusBadge({ children, tone = 'green' }: { children: React.ReactNode; tone?: 'green' | 'yellow' | 'gray' | 'red' }) {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>;
}
