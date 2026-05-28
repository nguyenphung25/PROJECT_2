import { ChevronLeft, ChevronRight } from 'lucide-react';
import styles from './Pagination.module.css';

export default function Pagination() {
  return (
    <div className={styles.pagination}>
      <button><ChevronLeft size={18} /></button>
      <button className={styles.active}>1</button>
      <button>2</button>
      <button>3</button>
      <button><ChevronRight size={18} /></button>
    </div>
  );
}
