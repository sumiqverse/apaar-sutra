import React, { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getAccessToken, apiClient, clearAuthTokens } from "@/lib/api";

interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  permissions: string[];
  institution_ids: string[];
}

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
  requiredPermission?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission,
}) => {
  const location = useLocation();
  const token = getAccessToken();

  const [, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthorized, setIsAuthorized] = useState(true);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }

    const checkAuth = async () => {
      try {
        const user = await apiClient<UserProfile>("/api/v1/auth/me");
        setProfile(user);

        if (requiredRole && !user.roles.includes(requiredRole) && !user.roles.includes("SUPER_ADMIN")) {
          setIsAuthorized(false);
        }

        if (
          requiredPermission &&
          !user.permissions.includes(requiredPermission) &&
          !user.permissions.includes("*:*") &&
          !user.roles.includes("SUPER_ADMIN")
        ) {
          setIsAuthorized(false);
        }
      } catch {
        clearAuthTokens();
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [token, requiredRole, requiredPermission]);

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-500 font-medium">Authenticating session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div className="p-8 max-w-lg mx-auto text-center space-y-4">
        <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
          <h2 className="text-base font-bold">Access Denied</h2>
          <p className="text-xs mt-1">Your user role does not have permission to view this resource.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
