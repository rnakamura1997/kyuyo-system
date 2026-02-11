import React, { useState } from 'react';
import {
  Box, Paper, Typography, Button, Grid, Card, CardContent,
  CardActions, TextField, MenuItem, Select, FormControl, InputLabel,
  Snackbar, Alert,
} from '@mui/material';
import { Download, TableChart, AccountBalance, Receipt, Assessment } from '@mui/icons-material';
import api from '@/services/api';

const currentYearMonth = () => {
  const now = new Date();
  return now.getFullYear() * 100 + (now.getMonth() + 1);
};

const ReportsPage: React.FC = () => {
  const [yearMonth, setYearMonth] = useState(currentYearMonth());
  const [periodId, setPeriodId] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

  const downloadReport = async (url: string, params: Record<string, any>, filename: string) => {
    try {
      const res = await api.get(url, { params, responseType: 'blob' });
      const blob = new Blob([res.data]);
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      setSnackbar({ open: true, message: 'ダウンロードしました', severity: 'success' });
    } catch {
      setSnackbar({ open: true, message: 'ダウンロードに失敗しました', severity: 'error' });
    }
  };

  const viewJson = async (url: string, params: Record<string, any>) => {
    try {
      const res = await api.get(url, { params });
      const w = window.open('', '_blank');
      if (w) {
        w.document.write(`<pre>${JSON.stringify(res.data, null, 2)}</pre>`);
      }
    } catch {
      setSnackbar({ open: true, message: '取得に失敗しました', severity: 'error' });
    }
  };

  const ymOptions: number[] = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date();
    d.setMonth(d.getMonth() - i);
    ymOptions.push(d.getFullYear() * 100 + (d.getMonth() + 1));
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 3 }}>帳票出力</Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>対象年月</InputLabel>
          <Select value={yearMonth} label="対象年月" onChange={(e) => setYearMonth(Number(e.target.value))}>
            {ymOptions.map((ym) => (
              <MenuItem key={ym} value={ym}>{Math.floor(ym / 100)}年{ym % 100}月</MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField size="small" label="給与期間ID" value={periodId} onChange={(e) => setPeriodId(e.target.value)} sx={{ width: 150 }} />
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <TableChart sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
              <Typography variant="h6">賃金台帳</Typography>
              <Typography variant="body2" color="text.secondary">月次の賃金台帳を出力します</Typography>
            </CardContent>
            <CardActions>
              <Button size="small" onClick={() => viewJson('/reports/payroll-ledger', { year_month: yearMonth })}>プレビュー</Button>
              <Button size="small" startIcon={<Download />} onClick={() => downloadReport('/reports/payroll-ledger', { year_month: yearMonth, format: 'csv' }, `payroll_ledger_${yearMonth}.csv`)}>CSV</Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <AccountBalance sx={{ fontSize: 48, color: 'success.main', mb: 1 }} />
              <Typography variant="h6">銀行振込データ</Typography>
              <Typography variant="body2" color="text.secondary">全銀フォーマットの振込データ</Typography>
            </CardContent>
            <CardActions>
              <Button size="small" startIcon={<Download />} disabled={!periodId} onClick={() => downloadReport('/reports/bank-transfer', { payroll_period_id: periodId }, `zengin_${periodId}.txt`)}>ダウンロード</Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Receipt sx={{ fontSize: 48, color: 'warning.main', mb: 1 }} />
              <Typography variant="h6">会計仕訳</Typography>
              <Typography variant="body2" color="text.secondary">会計ソフト連携用CSV</Typography>
            </CardContent>
            <CardActions>
              <Button size="small" startIcon={<Download />} disabled={!periodId} onClick={() => downloadReport('/reports/accounting-journal', { payroll_period_id: periodId }, `journal_${periodId}.csv`)}>CSV</Button>
            </CardActions>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Assessment sx={{ fontSize: 48, color: 'info.main', mb: 1 }} />
              <Typography variant="h6">月次集計</Typography>
              <Typography variant="body2" color="text.secondary">給与の月次サマリー</Typography>
            </CardContent>
            <CardActions>
              <Button size="small" onClick={() => viewJson('/reports/monthly-summary', { year_month: yearMonth })}>表示</Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default ReportsPage;
