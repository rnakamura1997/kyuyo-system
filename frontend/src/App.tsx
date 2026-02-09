/** メインアプリケーションコンポーネント */

import React, { useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { ThemeProvider, createTheme, CssBaseline } from "@mui/material";
import DashboardLayout from "./components/layout/DashboardLayout";
import LoginPage from "./pages/LoginPage";
import appRoutes from "./routes/routes";
import { useAuth } from "./hooks/useAuth";

const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2",
    },
    secondary: {
      main: "#dc004e",
    },
    success: {
      main: "#4caf50",
    },
    warning: {
      main: "#ff9800",
    },
    error: {
      main: "#f44336",
    },
  },
  typography: {
    fontFamily: ["Noto Sans JP", "Roboto", "sans-serif"].join(","),
  },
});

const AppInitializer: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { fetchMe } = useAuth();

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AppInitializer>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<DashboardLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              {appRoutes.map((route) => (
                <Route
                  key={route.path}
                  path={route.path}
                  element={route.element}
                />
              ))}
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AppInitializer>
      </BrowserRouter>
    </ThemeProvider>
  );
};

export default App;
