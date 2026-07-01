import {
  ArrowRightFromLine,
  ArrowRightToLine,
  Car,
  CheckCircle,
  Download,
  Eye,
  Filter,
  Search,
  Ticket,
} from "lucide-react";
import AppShell from "../../components/AppShell";
import PageHeader from "../../components/PageHeader";
import Plate from "../../components/Plate";
import Pagination from "../../components/Pagination";
import StatusBadge from "../../components/StatusBadge";
import { parkingRows } from "../../lib/data";
import styles from "./check-in-out.module.css";

export default function CheckInOutPage() {
  return (
    <AppShell active="check" searchPlaceholder="Tìm kiếm nhanh...">
      <PageHeader
        title="Quản lý Xe Ra/Vào"
        subtitle="Giám sát và điều phối hoạt động phương tiện thời gian thực."
        action={
          <div className={styles.capacityBox}>
            <strong>P</strong>
            <div>
              <span>TRỐNG</span>
              <b>142/500</b>
            </div>
          </div>
        }
      />

      <div className={styles.formGrid}>
        <section className={styles.panel}>
          <div className={styles.formTitle}>
            <span className={styles.greenIcon}>
              <ArrowRightToLine size={22} />
            </span>
            <h3>Xe Vào Bãi</h3>
          </div>
          <label>Biển Số Xe</label>
          <input className={styles.bigInput} placeholder="VD: 30A-123.45" />
          <label>Ghi Chú</label>
          <textarea placeholder="Thông tin thêm (nếu có)..." />
          <button className={styles.confirmIn}>
            <CheckCircle size={21} /> XÁC NHẬN VÀO
          </button>
        </section>

        <section className={styles.panel}>
          <div className={styles.formTitle}>
            <span className={styles.redIcon}>
              <ArrowRightFromLine size={22} />
            </span>
            <h3>Xe Ra Bãi</h3>
          </div>
          <label>Tìm kiếm Xe Ra</label>
          <div className={styles.exitSearch}>
            <Search size={24} />
            <span>
              NHẬP BIỂN SỐ ĐỂ
              <br />
              TÌM...
            </span>
          </div>
          <div className={styles.noteBox}>
            Quét thẻ hoặc nhập biển số để hiển thị thông tin phí gửi xe.
          </div>
          <button className={styles.confirmOut}>
            <Ticket size={21} /> XÁC NHẬN RA
          </button>
        </section>
      </div>

      <section className={styles.tableCard}>
        <div className={styles.tableHead}>
          <h3>
            <Car size={20} /> Xe Đang Trong Bãi <span>358 Xe</span>
          </h3>
          <div className={styles.tableActions}>
            <button>
              <Filter size={17} />
              Lọc
            </button>
            <button>
              <Download size={17} />
              Xuất Excel
            </button>
          </div>
        </div>
        <div className={styles.tableWrap}>
          <table>
            <thead>
              <tr>
                <th>STT</th>
                <th>BIỂN SỐ</th>
                <th>THỜI GIAN VÀO</th>
                <th>THỜI GIAN ĐỖ</th>
                <th>
                  GIÁ DỰ
                  <br />
                  KIẾN
                </th>
                <th>
                  TRẠNG
                  <br />
                  THÁI
                </th>
                <th>
                  THAO
                  <br />
                  TÁC
                </th>
              </tr>
            </thead>
            <tbody>
              {parkingRows.map((row) => (
                <tr key={row.stt}>
                  <td>{row.stt}</td>
                  <td>
                    <Plate value={row.plate.replace("-", "-\n")} />
                  </td>
                  <td>{row.timeIn}</td>
                  <td>{row.duration}</td>
                  <td>
                    <strong>{row.fee}</strong>
                  </td>
                  <td>
                    <StatusBadge tone={row.tone as "green" | "yellow"}>
                      {row.status}
                    </StatusBadge>
                  </td>
                  <td>
                    <Eye color="#063f7f" size={20} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={styles.tableFooter}>
          <p>Hiển thị 1-10 trên 358 xe</p>
          <Pagination />
        </div>
      </section>
    </AppShell>
  );
}
