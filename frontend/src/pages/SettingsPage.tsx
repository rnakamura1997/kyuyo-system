/** 設定ページ */

import React from "react";
import { Box, Typography } from "@mui/material";

export default function SettingsPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        設定
      </Typography>
      <Typography variant="body1" color="text.secondary">
        システムの各種設定を管理します。ユーザー管理、税率設定、保険料率設定などが行えます。
      </Typography>
    </Box>
  );
}
