/** 認証フック */

import { useAuthStore } from "../store/authStore";

export function useAuth() {
  const { user, isAuthenticated, isLoading, login, logout, fetchMe } =
    useAuthStore();
  return { user, isAuthenticated, isLoading, login, logout, fetchMe };
}

export function usePermission() {
  const { user } = useAuthStore();

  const hasRole = (roles: string | string[]): boolean => {
    if (!user) return false;
    if (user.is_super_admin) return true;
    const roleArray = Array.isArray(roles) ? roles : [roles];
    return roleArray.some((role) => user.roles.includes(role));
  };

  return { hasRole };
}
