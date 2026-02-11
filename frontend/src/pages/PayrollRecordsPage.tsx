import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Paper, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Grid, Card, CardContent,
  CircularProgress, Divider,
} from '@mui/material';
import { ArrowBack, PictureAsPdf, Print } from '@mui/icons-material';
import api from '@/services/api';

interface PayrollItem {
  id: number;
  item_type: string;
  item_code: string;
  item_name: string;
  amount: number;
  is_taxable: boolean;
}

interface PayrollDetail {
  id: number;
  employee_id: number;
  version: number;
  status: string;
  payment_date: string;
  total_earnings: number;
  total_deductions: number;
  net_pay: number;
  items: PayrollItem[];
  calculation_details: Record<string, any> | null;
}

const fmt = (n: number) => '¥' + n.toLocaleString('ja-JP');

const PayrollRecordsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<PayrollDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const fetchDetail = async () => {
      try {
        const res = await api.get(`/payroll/records/${id}`);
        setDetail(res.data);
      } catch { /* ignore */ }
      setLoading(false);
    };
    fetchDetail();
  }, [id]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  if (!detail) return <Typography>データが見つかりません</Typography>;

  const earnings = detail.items.filter((i) => i.item_type === 'earning');
  const deductions = detail.items.filter((i) => i.item_type === 'deduction');

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate(-1)}>戻る</Button>
          <Typography variant="h5">給与明細詳細</Typography>
          <Chip label={detail.status === 'confirmed' ? '確定' : detail.status === 'draft' ? '下書き' : '取消'} color={detail.status === 'confirmed' ? 'success' : detail.status === 'draft' ? 'warning' : 'error'} />
        </Box>
        <Button variant="outlined" startIcon={<Print />} onClick={() => window.print()}>印刷</Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card><CardContent>
            <Typography variant="subtitle2" color="text.secondary">支給額合計</Typography>
            <Typography variant="h4" color="primary">{fmt(detail.total_earnings)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card><CardContent>
            <Typography variant="subtitle2" color="text.secondary">控除額合計</Typography>
            <Typography variant="h4" color="error">{fmt(detail.total_deductions)}</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card><CardContent>
            <Typography variant="subtitle2" color="text.secondary">差引支給額</Typography>
            <Typography variant="h4" sx={{ fontWeight: 'bold' }}>{fmt(detail.net_pay)}</Typography>
          </CardContent></Card>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 1 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>支給項目</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>項目名</TableCell>
                  <TableCell align="right">金額</TableCell>
                  <TableCell align="center">課税</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {earnings.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.item_name}</TableCell>
                    <TableCell align="right">{fmt(item.amount)}</TableCell>
                    <TableCell align="center">{item.is_taxable ? '○' : '−'}</TableCell>
                  </TableRow>
                ))}
                <TableRow sx={{ '& td': { fontWeight: 'bold' } }}>
                  <TableCell>合計</TableCell>
                  <TableCell align="right">{fmt(detail.total_earnings)}</TableCell>
                  <TableCell />
                </TableRow>
              </TableBody>
            </Table>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>控除項目</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>項目名</TableCell>
                  <TableCell align="right">金額</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {deductions.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.item_name}</TableCell>
                    <TableCell align="right">{fmt(item.amount)}</TableCell>
                  </TableRow>
                ))}
                <TableRow sx={{ '& td': { fontWeight: 'bold' } }}>
                  <TableCell>合計</TableCell>
                  <TableCell align="right">{fmt(detail.total_deductions)}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default PayrollRecordsPage;
