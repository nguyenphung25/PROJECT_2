import { BarChart3, Camera, Car, Clock, LogIn, Users } from "lucide-react";
import AppShell from "../../components/AppShell";
import PageHeader from "../../components/PageHeader";
import { activities, shortcuts } from "../../lib/data";
import styles from "./dashboard.module.css";

export default function DashboardPage() {
  const statCards = [
    { label: "XE ĐANG\nTRONG BÃI", value: "1", icon: Car },
    { label: "TỔNG XE HÔM\nNAY", value: "2", icon: Camera },
    { label: "XE ĐÃ RA", value: "1", icon: LogIn },
    { label: "THỜI GIAN EO\nTB", value: "0h", icon: Clock },
  ];

  return (
    <AppShell
      active="dashboard"
      searchPlaceholder="Tìm kiếm giao dịch, biển số xe..."
      userName="Admin"
      role="SUPERUSER"
    >
      <PageHeader
        title="Chào mừng đến với Dashboard"
        subtitle="Hệ thống quản lý bãi đỗ xe ParkingPro đang hoạt động bình thường."
      />

      <div className={styles.statsGrid}>
        {statCards.map((item) => {
          const Icon = item.icon;
          return (
            <div className={styles.statCard} key={item.label}>
              <div className={styles.statIcon}>
                <Icon size={22} />
              </div>
              <div>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.analyticsGrid}>
        <section className={styles.chartCard}>
          <div className={styles.cardTitleRow}>
            <h3>Lưu lượng xe trong ngày</h3>
            <div>
              <span className={styles.live}>LIVE</span> Hôm nay, 15 Thg 10
            </div>
          </div>
          <div className={styles.chartArea}>
            {[52, 92, 174, 126, 150, 72, 44].map((height, index) => (
              <div
                className={`${styles.bar} ${index === 3 ? styles.activeBar : ""}`}
                style={{ height }}
                key={index}
              />
            ))}
          </div>
          <div className={styles.chartAxis}>
            <span>06:00</span>
            <span>09:00</span>
            <span>12:00</span>
            <span>15:00</span>
            <span>18:00</span>
            <span>21:00</span>
          </div>
        </section>

        <section className={styles.activityCard}>
          <h3>Hoạt động gần đây</h3>
          <div className={styles.activityList}>
            {activities.map((item) => (
              <div className={styles.activityItem} key={item.title}>
                <span className={`${styles.dotIcon} ${styles[item.tone]}`}>
                  ↪
                </span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <button className={styles.outlineBtn}>Xem tất cả lịch sử</button>
        </section>
      </div>

      <h3 className={styles.sectionTitle}>Lối tắt chức năng</h3>
      <div className={styles.shortcutsGrid}>
        {shortcuts.map((item, index) => (
          <div className={styles.shortcutCard} key={item.title}>
            <div className={styles.shortcutIcon}>
              {index === 0 ? (
                <Camera size={20} />
              ) : index === 1 ? (
                <Users size={20} />
              ) : index === 2 ? (
                <LogIn size={20} />
              ) : (
                <BarChart3 size={20} />
              )}
            </div>
            <strong>{item.title}</strong>
            <p>{item.desc}</p>
          </div>
        ))}
      </div>

      <section className={styles.heroBanner}>
        <div>
          <h3>Tối ưu hóa không gian bãi đỗ</h3>
          <p>
            Sử dụng công nghệ AI để dự báo nhu cầu đỗ xe và đề xuất các phương
            án tối ưu hóa mặt bằng.
          </p>
          <button>Xem phân tích AI</button>
        </div>
      </section>
    </AppShell>
  );
}
