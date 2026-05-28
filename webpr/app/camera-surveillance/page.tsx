"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Upload,
  Image as ImageIcon,
  ClipboardCheck,
  RefreshCcw,
  Download,
  Filter,
  Car,
  Bike,
  AlertCircle,
} from "lucide-react";

import AppShell from "../../components/AppShell";
import Plate from "../../components/Plate";
import StatusBadge from "../../components/StatusBadge";
import styles from "./camera-surveillance.module.css";

type DetectionStatus = "success" | "failed" | "pending";

type Detection = {
  id: string;
  file_name: string | null;
  image_url: string | null;
  detected_plate: string | null;
  vehicle_type: string | null;
  confidence: number | null;
  detection_status: DetectionStatus;
  note: string | null;
  created_at: string;
};

export default function CameraSurveillancePage() {
  const [detections, setDetections] = useState<Detection[]>([]);

  const latest = detections[0];

  const loadDetections = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:5000/detections/latest", {
        cache: "no-store",
      });

      const json = await res.json();

      if (json.success) {
        setDetections(json.data || []);
      }
    } catch (error) {
      console.error("Không lấy được dữ liệu nhận diện:", error);
    }
  }, []);
  useEffect(() => {
    const timer = setInterval(() => {
      loadDetections();
    }, 2000);

    return () => clearInterval(timer);
  }, [loadDetections]);
  const successCount = useMemo(() => {
    return detections.filter((item) => item.detection_status === "success")
      .length;
  }, [detections]);

  const failedCount = useMemo(() => {
    return detections.filter((item) => item.detection_status === "failed")
      .length;
  }, [detections]);

  const accuracyRate = useMemo(() => {
    if (detections.length === 0) return 0;

    return Math.round((successCount / detections.length) * 100);
  }, [detections.length, successCount]);

  const getVehicleLabel = (vehicleType?: string | null) => {
    if (vehicleType === "motorbike") return "Xe máy";
    if (vehicleType === "car") return "Ô tô";
    return "unknown";
  };

  const getTime = (value?: string | null) => {
    if (!value) return "--";

    return new Date(value).toLocaleTimeString("vi-VN");
  };

  const getStatusText = (status?: DetectionStatus) => {
    if (status === "success") return "Đã nhận diện";
    if (status === "failed") return "Không hợp lệ";
    return "Đang chờ";
  };

  return (
    <AppShell
      active="camera"
      searchPlaceholder="Tìm kiếm ảnh, biển số hoặc mã lượt..."
      userName="Alex Nguyen"
      role="Quản lý cổng"
    >
      <div className={styles.headRow}>
        <div>
          <h2>Nhận Diện Biển Số Từ Camera</h2>
          <p>
            IR phát hiện xe, webcam tự động chụp ảnh, nhận diện biển số và lưu
            vào database.
          </p>
        </div>

        <div className={styles.headActions}>
          <button onClick={loadDetections}>
            <RefreshCcw size={19} />
            Làm mới
          </button>

          <button className={styles.primaryAction} onClick={loadDetections}>
            <Upload size={19} />
            Cập nhật ảnh mới
          </button>
        </div>
      </div>

      <div className={styles.cameraGrid}>
        <section className={styles.uploadPanel}>
          <div className={styles.panelTitle}>
            <h3>
              <ImageIcon size={22} />
              Ảnh Cần Nhận Diện
            </h3>

            <span className={styles.imageMode}>CAMERA TỰ ĐỘNG</span>
          </div>

          <div className={styles.previewCard}>
            <div className={styles.previewTop}>
              <div>
                <strong>Ảnh camera vừa chụp</strong>
                <p>{latest?.file_name || "Chưa có ảnh"}</p>
              </div>

              <StatusBadge
                tone={
                  latest?.detection_status === "success" ? "green" : "yellow"
                }
              >
                {getStatusText(latest?.detection_status)}
              </StatusBadge>
            </div>

            <div
              className={styles.previewImage}
              style={{
                backgroundImage: latest?.image_url
                  ? `url(${latest.image_url})`
                  : undefined,
              }}
            >
              {!latest?.image_url && (
                <div className={styles.emptyPreview}>Chưa có ảnh từ camera</div>
              )}

              <div className={styles.scanLabel}>VÙNG BIỂN SỐ</div>
              <div className={styles.detectBox}></div>
            </div>

            <div className={styles.actionRow}>
              <button
                className={styles.secondaryButton}
                onClick={loadDetections}
              >
                Làm mới
              </button>

              <button className={styles.detectButton} onClick={loadDetections}>
                <ClipboardCheck size={20} />
                Cập nhật kết quả
              </button>
            </div>
          </div>
        </section>

        <aside className={styles.resultPanel}>
          <h3>
            <ClipboardCheck size={21} />
            Kết Quả Nhận Diện
          </h3>

          <span className={styles.resultLabel}>BIỂN SỐ PHÁT HIỆN</span>

          <Plate value={latest?.detected_plate || "--"} large />

          <div className={styles.confGrid}>
            <div>
              <span>Độ tin cậy</span>
              <strong>
                {latest?.confidence !== null && latest?.confidence !== undefined
                  ? `${latest.confidence}%`
                  : "--"}
              </strong>
            </div>

            <div>
              <span>Loại xe</span>
              <strong>{getVehicleLabel(latest?.vehicle_type)}</strong>
            </div>
          </div>

          <div className={styles.resultLine}>
            <span>Thời gian xử lý</span>
            <b>{getTime(latest?.created_at)}</b>
          </div>

          <div className={styles.resultLine}>
            <span>Trạng thái</span>
            <b className={styles.guest}>
              {latest?.detection_status === "success"
                ? "HỢP LỆ"
                : latest?.detection_status === "failed"
                  ? "KHÔNG HỢP LỆ"
                  : "ĐANG CHỜ"}
            </b>
          </div>

          <button className={styles.approveBtn}>Đã lưu vào database</button>
        </aside>
      </div>

      <div className={styles.metricsGrid}>
        <div className={styles.metric}>
          <span>Ảnh đã xử lý</span>
          <strong>{detections.length}</strong>
          <p>Dữ liệu lấy từ Supabase</p>
        </div>

        <div className={styles.metric}>
          <span>Nhận diện thành công</span>
          <strong>{successCount}</strong>
          <p>Biển số hợp lệ</p>
        </div>

        <div className={styles.metric}>
          <span>Ảnh lỗi</span>
          <strong>{failedCount}</strong>
          <p>Cần kiểm tra thủ công</p>
        </div>

        <div className={styles.metric}>
          <span>Tỉ lệ chính xác</span>
          <strong>{accuracyRate}%</strong>

          <div className={styles.progress}>
            <i style={{ width: `${accuracyRate}%` }} />
          </div>
        </div>
      </div>

      <section className={styles.tableCard}>
        <div className={styles.tableTop}>
          <h3>Lịch Sử Nhận Diện Ảnh</h3>

          <div>
            <button onClick={loadDetections}>
              <Filter size={18} />
            </button>

            <button onClick={loadDetections}>
              <Download size={18} />
            </button>
          </div>
        </div>

        <div className={styles.tableWrap}>
          <table>
            <thead>
              <tr>
                <th>STT</th>
                <th>TÊN ẢNH</th>
                <th>BIỂN SỐ</th>
                <th>LOẠI XE</th>
                <th>ĐỘ TIN CẬY</th>
                <th>THỜI GIAN</th>
                <th>TRẠNG THÁI</th>
              </tr>
            </thead>

            <tbody>
              {detections.length === 0 ? (
                <tr>
                  <td colSpan={7}>Chưa có dữ liệu nhận diện</td>
                </tr>
              ) : (
                detections.map((item, index) => (
                  <tr key={item.id}>
                    <td>{index + 1}</td>

                    <td>
                      <div className={styles.fileName}>
                        <ImageIcon size={17} />
                        {item.file_name || "unknown.jpg"}
                      </div>
                    </td>

                    <td>
                      <strong>{item.detected_plate || "--"}</strong>
                    </td>

                    <td>
                      {item.vehicle_type === "motorbike" ? (
                        <Bike size={16} />
                      ) : item.vehicle_type === "car" ? (
                        <Car size={16} />
                      ) : (
                        <AlertCircle size={16} />
                      )}

                      {getVehicleLabel(item.vehicle_type)}
                    </td>

                    <td>
                      {item.confidence !== null && item.confidence !== undefined
                        ? `${item.confidence}%`
                        : "--"}
                    </td>

                    <td>{getTime(item.created_at)}</td>

                    <td>
                      <StatusBadge
                        tone={
                          item.detection_status === "success"
                            ? "green"
                            : "yellow"
                        }
                      >
                        {getStatusText(item.detection_status)}
                      </StatusBadge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
