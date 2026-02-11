/** ダッシュボードページ */

import { Box, Card, CardContent, Grid, Typography } from "@mui/material";

const summaryCards = [
  { title: "従業員数", value: "-", description: "登録済み従業員の総数" },
  { title: "今月の給与処理", value: "-", description: "当月の給与計算状況" },
  { title: "未処理の勤怠", value: "-", description: "承認待ちの勤怠データ" },
  { title: "会社数", value: "-", description: "登録済み会社の総数" },
];

export default function DashboardPage() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        ダッシュボード
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        給与システムの概要を表示します。
      </Typography>
      <Grid container spacing={3}>
        {summaryCards.map((card) => (
          <Grid item xs={12} sm={6} md={3} key={card.title}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  {card.title}
                </Typography>
                <Typography variant="h4" sx={{ my: 1 }}>
                  {card.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {card.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
