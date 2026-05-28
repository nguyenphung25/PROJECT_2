import styles from './Plate.module.css';

export default function Plate({ value, large = false }: { value: string; large?: boolean }) {
  return <span className={`${styles.plate} ${large ? styles.large : ''}`}>{value}</span>;
}
