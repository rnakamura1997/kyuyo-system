/** メニュー自動生成ユーティリティ */

import type { ExtendedRouteObject } from "../routes/routes";

export interface MenuItem {
  path: string;
  title: string;
  icon?: string;
  order: number;
  group: string;
  children?: MenuItem[];
}

export interface MenuGroup {
  name: string;
  label: string;
  items: MenuItem[];
}

const GROUP_LABELS: Record<string, string> = {
  main: "メイン",
  master: "マスタ管理",
  payroll: "給与管理",
  tax: "税務",
  reports: "帳票・レポート",
  settings: "設定",
  other: "その他",
};

const GROUP_ORDER: Record<string, number> = {
  main: 0,
  master: 1,
  payroll: 2,
  tax: 3,
  reports: 4,
  settings: 5,
  other: 99,
};

/**
 * ルーティング定義からメニュー項目を抽出
 */
export function generateMenuItems(
  routes: ExtendedRouteObject[],
  userRoles: string[],
  isSuperAdmin: boolean,
  basePath: string = ""
): MenuItem[] {
  const items: MenuItem[] = [];

  routes.forEach((route) => {
    if (!route.meta || !route.meta.inMenu) return;

    // 権限チェック
    if (!isSuperAdmin) {
      const hasPermission = route.meta.requiredRoles.some((role) =>
        userRoles.includes(role)
      );
      if (!hasPermission) return;
    }

    const fullPath = basePath ? `${basePath}/${route.path}` : `/${route.path}`;

    const item: MenuItem = {
      path: fullPath,
      title: route.meta.title,
      icon: route.meta.icon,
      order: route.meta.order || 999,
      group: route.meta.group || "other",
      children: route.children
        ? generateMenuItems(route.children, userRoles, isSuperAdmin, fullPath)
        : undefined,
    };

    items.push(item);
  });

  return items.sort((a, b) => a.order - b.order);
}

/**
 * メニュー項目をグループ化
 */
export function groupMenuItems(items: MenuItem[]): MenuGroup[] {
  const groups = new Map<string, MenuItem[]>();

  items.forEach((item) => {
    const groupName = item.group;
    if (!groups.has(groupName)) {
      groups.set(groupName, []);
    }
    groups.get(groupName)!.push(item);
  });

  return Array.from(groups.entries())
    .map(([name, items]) => ({
      name,
      label: GROUP_LABELS[name] || name,
      items,
    }))
    .sort(
      (a, b) => (GROUP_ORDER[a.name] || 99) - (GROUP_ORDER[b.name] || 99)
    );
}
