/** サイドバーコンポーネント（自動メニュー生成） */

import React, { useMemo } from "react";
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Box,
  Toolbar,
} from "@mui/material";
import { useNavigate, useLocation } from "react-router-dom";
import * as Icons from "@mui/icons-material";
import { useAuth } from "../../hooks/useAuth";
import appRoutes from "../../routes/routes";
import { generateMenuItems, groupMenuItems } from "../../utils/menuGenerator";

const DRAWER_WIDTH = 260;

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const userRoles = user?.roles || [];
  const isSuperAdmin = user?.is_super_admin || false;

  const groupedMenus = useMemo(() => {
    const items = generateMenuItems(
      appRoutes,
      userRoles,
      isSuperAdmin
    );
    return groupMenuItems(items);
  }, [userRoles, isSuperAdmin]);

  const getIcon = (iconName?: string) => {
    if (!iconName) return null;
    const IconComponent = (Icons as Record<string, React.ComponentType>)[
      iconName
    ];
    return IconComponent ? React.createElement(IconComponent) : null;
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          boxSizing: "border-box",
        },
      }}
    >
      <Toolbar>
        <Typography variant="h6" noWrap sx={{ fontWeight: 700 }}>
          給与明細管理
        </Typography>
      </Toolbar>
      <Divider />

      {groupedMenus.map((group, groupIndex) => (
        <React.Fragment key={group.name}>
          {groupIndex > 0 && <Divider />}
          <Box sx={{ px: 2, pt: 2, pb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              {group.label}
            </Typography>
          </Box>
          <List disablePadding>
            {group.items.map((item) => (
              <ListItem key={item.path} disablePadding>
                <ListItemButton
                  selected={location.pathname === item.path}
                  onClick={() => navigate(item.path)}
                  sx={{ pl: 3 }}
                >
                  {item.icon && (
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      {getIcon(item.icon)}
                    </ListItemIcon>
                  )}
                  <ListItemText primary={item.title} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </React.Fragment>
      ))}
    </Drawer>
  );
};

export default Sidebar;
