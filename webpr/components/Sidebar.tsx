"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ArrowRightLeft,
  BadgeDollarSign,
  Camera,
  LogOut,
} from "lucide-react";
import styles from "./Sidebar.module.css";
import Image from "next/image";

const menuItems = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: "Check-in/out",
    href: "/check-in-out",
    icon: ArrowRightLeft,
  },
  {
    label: "Price Management",
    href: "/price-management",
    icon: BadgeDollarSign,
  },
  {
    label: "Camera Surveillance",
    href: "/camera-surveillance",
    icon: Camera,
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className={styles.sidebar}>
      <div>
        <div className={styles.brand}>
          <div className={styles.logo}>P</div>

          <div>
            <h1>ParkingPro</h1>
            <p>Admin Terminal</p>
          </div>
        </div>

        <nav className={styles.nav}>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`${styles.navItem} ${isActive ? styles.active : ""}`}
              >
                <Icon size={21} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className={styles.bottom}>
        <div className={styles.userBox}>
          <Image
            src="https://i.pravatar.cc/80?img=12"
            alt="Admin avatar"
            width={80}
            height={80}
            className={styles.avatar}
            unoptimized
          />

          <div>
            <h4>Admin</h4>
            <p>SUPERUSER</p>
          </div>
        </div>

        <button className={styles.logout}>
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}
