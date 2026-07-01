import {
  Bike,
  CalendarDays,
  Car,
  Edit,
  Filter,
  Plus,
  Trash2,
  TrendingUp,
  Truck,
} from "lucide-react";
import AppShell from "../../components/AppShell";
import PageHeader from "../../components/PageHeader";
import Pagination from "../../components/Pagination";
import { priceRows } from "../../lib/data";
import styles from "./price-management.module.css";

function VehicleIcon({ type }: { type: string }) {
  if (type === "car") return <Car size={19} />;
  if (type === "truck") return <Truck size={19} />;
  return <Bike size={19} />;
}

export default function PriceManagementPage() {
  const cards = [
    { icon: Car, label: "Ô TÔ (GIỜ)", value: "25.000đ" },
    { icon: Bike, label: "XE MÁY (LƯỢT)", value: "5.000đ" },
    { icon: CalendarDays, label: "VÉ THÁNG CAO\nNHẤT", value: "1.200k" },
    {
      icon: TrendingUp,
      label: "THAY ĐỔI GẦN\nNHẤT",
      value: "2 giờ trước",
      small: true,
    },
  ];

  return (
    <AppShell active="price" searchPlaceholder="Tìm kiếm giá vé...">
      <PageHeader
        title="Quản Lý Bảng Giá"
        subtitle="Thiết lập và cập nhật đơn giá đỗ xe cho các loại phương tiện."
        action={
          <button className={styles.addBtn}>
            <Plus size={20} /> Thêm Giá Mới
          </button>
        }
      />

      <div className={styles.summaryGrid}>
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div className={styles.summaryCard} key={card.label}>
              <Icon size={20} />
              <span>{card.label}</span>
              <strong className={card.small ? styles.smallValue : ""}>
                {card.value}
              </strong>
            </div>
          );
        })}
      </div>

      <section className={styles.tableCard}>
        <div className={styles.tabsRow}>
          <div className={styles.tabs}>
            <button className={styles.active}>Tất cả</button>
            <button>Xe máy</button>
            <button>Ô tô</button>
            <button>Xe đạp</button>
          </div>
          <div className={styles.sort}>
            Sắp xếp: <strong>Loại xe</strong> <Filter size={19} />
          </div>
        </div>
        <div className={styles.tableWrap}>
          <table>
            <thead>
              <tr>
                <th>STT</th>
                <th>LOẠI XE</th>
                <th>
                  CA
                  <br />
                  TRỰC
                </th>
                <th>
                  GIÁ THEO
                  <br />
                  GIỜ
                </th>
                <th>
                  GIÁ THEO
                  <br />
                  CA
                </th>
                <th>VÉ NGÀY</th>
                <th>VÉ THÁNG</th>
                <th>THAO TÁC</th>
              </tr>
            </thead>
            <tbody>
              {priceRows.map((row) => (
                <tr key={row.stt}>
                  <td>{row.stt}</td>
                  <td>
                    <div className={styles.vehicleCell}>
                      <span>
                        <VehicleIcon type={row.vehicle} />
                      </span>
                      <b>{row.type}</b>
                    </div>
                  </td>
                  <td>
                    <span className={`${styles.shift} ${styles[row.tone]}`}>
                      {row.shift}
                    </span>
                  </td>
                  <td>{row.hourly}</td>
                  <td>{row.session}</td>
                  <td>{row.day}</td>
                  <td>{row.month}</td>
                  <td>
                    <div className={styles.actions}>
                      <Edit size={18} />
                      <Trash2 size={18} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={styles.footer}>
          <p>Hiển thị 1-4 trong số 12 loại giá</p>
          <Pagination />
        </div>
      </section>

      <section className={styles.tipBox}>
        <div className={styles.info}>i</div>
        <div>
          <h3>Mẹo Quản Lý Giá</h3>
          <p>
            Hệ thống sẽ tự động áp dụng giá theo Ca nếu thời gian đỗ xe vượt quá
            4 giờ liên tục. Đảm bảo cấu hình giá Vé Tháng thấp hơn tổng chi phí
            Vé Ngày để khuyến khích khách hàng đăng ký dài hạn.
          </p>
        </div>
      </section>
    </AppShell>
  );
}
