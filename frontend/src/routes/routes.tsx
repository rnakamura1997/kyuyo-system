/** ルーティング定義（メタ情報付き自動メニュー生成方式） */

import { lazy } from "react";
import type { ReactNode } from "react";

// ページコンポーネント（遅延読み込み）
const DashboardPage = lazy(() => import("../pages/DashboardPage"));
const CompaniesPage = lazy(() => import("../pages/CompaniesPage"));
const EmployeesPage = lazy(() => import("../pages/EmployeesPage"));
const AttendancePage = lazy(() => import("../pages/AttendancePage"));
const PayrollPage = lazy(() => import("../pages/PayrollPage"));
const PayrollRecordsPage = lazy(() => import("../pages/PayrollRecordsPage"));
const YearEndAdjustmentPage = lazy(
  () => import("../pages/YearEndAdjustmentPage")
);
const ReportsPage = lazy(() => import("../pages/ReportsPage"));
const SettingsPage = lazy(() => import("../pages/SettingsPage"));

export interface RouteMetadata {
  title: string;
  icon?: string;
  inMenu: boolean;
  requiredRoles: string[];
  order?: number;
  group?: string;
}

export interface ExtendedRouteObject {
  path: string;
  element: ReactNode;
  meta?: RouteMetadata;
  children?: ExtendedRouteObject[];
}

const appRoutes: ExtendedRouteObject[] = [
  {
    path: "dashboard",
    element: <DashboardPage />,
    meta: {
      title: "ダッシュボード",
      icon: "Dashboard",
      inMenu: true,
      requiredRoles: ["super_admin", "admin", "accountant", "employee"],
      order: 1,
      group: "main",
    },
  },
  {
    path: "companies",
    element: <CompaniesPage />,
    meta: {
      title: "会社管理",
      icon: "Business",
      inMenu: true,
      requiredRoles: ["super_admin"],
      order: 10,
      group: "master",
    },
  },
  {
    path: "employees",
    element: <EmployeesPage />,
    meta: {
      title: "従業員管理",
      icon: "People",
      inMenu: true,
      requiredRoles: ["super_admin", "admin"],
      order: 11,
      group: "master",
    },
  },
  {
    path: "attendance",
    element: <AttendancePage />,
    meta: {
      title: "勤怠データ",
      icon: "AccessTime",
      inMenu: true,
      requiredRoles: ["super_admin", "admin", "accountant"],
      order: 20,
      group: "payroll",
    },
  },
  {
    path: "payroll",
    element: <PayrollPage />,
    meta: {
      title: "給与計算",
      icon: "AttachMoney",
      inMenu: true,
      requiredRoles: ["super_admin", "admin", "accountant"],
      order: 21,
      group: "payroll",
    },
  },
  {
    path: "payroll-records",
    element: <PayrollRecordsPage />,
    meta: {
      title: "給与明細一覧",
      icon: "Description",
      inMenu: true,
      requiredRoles: ["super_admin", "admin", "accountant", "employee"],
      order: 22,
      group: "payroll",
    },
  },
  {
    path: "payroll-records/:id",
    element: <PayrollRecordsPage />,
    meta: {
      title: "給与明細詳細",
      icon: "Description",
      inMenu: false,
      requiredRoles: ["super_admin", "admin", "accountant", "employee"],
    },
  },
  {
    path: "year-end-adjustment",
    element: <YearEndAdjustmentPage />,
    meta: {
      title: "年末調整",
      icon: "Assignment",
      inMenu: true,
      requiredRoles: ["super_admin", "admin", "accountant", "employee"],
      order: 30,
      group: "tax",
    },
  },
  {
    path: "reports",
    element: <ReportsPage />,
    meta: {
      title: "帳票出力",
      icon: "Assessment",
      inMenu: true,
      requiredRoles: ["super_admin", "admin", "accountant"],
      order: 40,
      group: "reports",
    },
  },
  {
    path: "settings",
    element: <SettingsPage />,
    meta: {
      title: "システム設定",
      icon: "Settings",
      inMenu: true,
      requiredRoles: ["super_admin", "admin"],
      order: 50,
      group: "settings",
    },
  },
];

export default appRoutes;
