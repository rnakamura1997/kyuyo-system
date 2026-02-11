import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Tab, Tabs, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Snackbar, Alert,
  CircularProgress, IconButton, Switch, FormControlLabel, Grid,
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import api from '@/services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <Box role="tabpanel" hidden={value !== index} sx={{ pt: 2 }}>
    {value === index && children}
  </Box>
);

// --- Users Tab ---
const UsersTab: React.FC = () => {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editData, setEditData] = useState<any>({});
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

  const fetch = useCallback(async () => {
    setLoading(true);
    try { const res = await api.get('/users'); setUsers(res.data.items); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleSave = async () => {
    try {
      if (editData.id) {
        await api.put(`/users/${editData.id}`, editData);
      } else {
        await api.post('/users', editData);
      }
      setSnackbar({ open: true, message: '保存しました', severity: 'success' });
      setEditOpen(false);
      fetch();
    } catch { setSnackbar({ open: true, message: '保存に失敗しました', severity: 'error' }); }
  };

  const handleToggle = async (id: number) => {
    try {
      await api.put(`/users/${id}/toggle-active`);
      fetch();
    } catch {}
  };

  if (loading) return <CircularProgress />;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button variant="contained" startIcon={<Add />} onClick={() => { setEditData({ role_codes: ['admin'] }); setEditOpen(true); }}>ユーザー追加</Button>
      </Box>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>ユーザー名</TableCell>
              <TableCell>メール</TableCell>
              <TableCell>氏名</TableCell>
              <TableCell>有効</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map((u) => (
              <TableRow key={u.id}>
                <TableCell>{u.id}</TableCell>
                <TableCell>{u.username}</TableCell>
                <TableCell>{u.email}</TableCell>
                <TableCell>{u.full_name}</TableCell>
                <TableCell><Switch checked={u.is_active} onChange={() => handleToggle(u.id)} /></TableCell>
                <TableCell align="center">
                  <IconButton onClick={() => { setEditData(u); setEditOpen(true); }}><Edit /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editData.id ? 'ユーザー編集' : 'ユーザー追加'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6}><TextField fullWidth label="ユーザー名" value={editData.username || ''} onChange={(e) => setEditData({ ...editData, username: e.target.value })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="メール" value={editData.email || ''} onChange={(e) => setEditData({ ...editData, email: e.target.value })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="氏名" value={editData.full_name || ''} onChange={(e) => setEditData({ ...editData, full_name: e.target.value })} /></Grid>
            {!editData.id && <Grid item xs={6}><TextField fullWidth label="パスワード" type="password" value={editData.password || ''} onChange={(e) => setEditData({ ...editData, password: e.target.value })} /></Grid>}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>キャンセル</Button>
          <Button variant="contained" onClick={handleSave}>保存</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

// --- AllowanceTypes Tab ---
const AllowanceTypesTab: React.FC = () => {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editData, setEditData] = useState<any>({});
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({ open: false, message: '', severity: 'success' });

  const fetch = useCallback(async () => {
    setLoading(true);
    try { const res = await api.get('/allowance-types'); setItems(res.data.items); } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const handleSave = async () => {
    try {
      if (editData.id) {
        await api.put(`/allowance-types/${editData.id}`, editData);
      } else {
        await api.post('/allowance-types', editData);
      }
      setSnackbar({ open: true, message: '保存しました', severity: 'success' });
      setEditOpen(false);
      fetch();
    } catch { setSnackbar({ open: true, message: '保存に失敗しました', severity: 'error' }); }
  };

  if (loading) return <CircularProgress />;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button variant="contained" startIcon={<Add />} onClick={() => { setEditData({ is_taxable: true, is_social_insurance_target: true, is_employment_insurance_target: true }); setEditOpen(true); }}>手当種別追加</Button>
      </Box>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>コード</TableCell>
              <TableCell>名称</TableCell>
              <TableCell>課税</TableCell>
              <TableCell>社保対象</TableCell>
              <TableCell>雇保対象</TableCell>
              <TableCell>割増基礎</TableCell>
              <TableCell align="center">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((a) => (
              <TableRow key={a.id}>
                <TableCell>{a.code}</TableCell>
                <TableCell>{a.name}</TableCell>
                <TableCell>{a.is_taxable ? '○' : '×'}</TableCell>
                <TableCell>{a.is_social_insurance_target ? '○' : '×'}</TableCell>
                <TableCell>{a.is_employment_insurance_target ? '○' : '×'}</TableCell>
                <TableCell>{a.is_overtime_base ? '○' : '×'}</TableCell>
                <TableCell align="center">
                  <IconButton onClick={() => { setEditData(a); setEditOpen(true); }}><Edit /></IconButton>
                  <IconButton color="error" onClick={async () => { await api.delete(`/allowance-types/${a.id}`); fetch(); }}><Delete /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editData.id ? '手当種別編集' : '手当種別追加'}</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={6}><TextField fullWidth label="コード" value={editData.code || ''} onChange={(e) => setEditData({ ...editData, code: e.target.value })} /></Grid>
            <Grid item xs={6}><TextField fullWidth label="名称" value={editData.name || ''} onChange={(e) => setEditData({ ...editData, name: e.target.value })} /></Grid>
            <Grid item xs={6}><FormControlLabel control={<Switch checked={editData.is_taxable ?? true} onChange={(e) => setEditData({ ...editData, is_taxable: e.target.checked })} />} label="課税対象" /></Grid>
            <Grid item xs={6}><FormControlLabel control={<Switch checked={editData.is_social_insurance_target ?? true} onChange={(e) => setEditData({ ...editData, is_social_insurance_target: e.target.checked })} />} label="社保対象" /></Grid>
            <Grid item xs={6}><FormControlLabel control={<Switch checked={editData.is_employment_insurance_target ?? true} onChange={(e) => setEditData({ ...editData, is_employment_insurance_target: e.target.checked })} />} label="雇保対象" /></Grid>
            <Grid item xs={6}><FormControlLabel control={<Switch checked={editData.is_overtime_base ?? false} onChange={(e) => setEditData({ ...editData, is_overtime_base: e.target.checked })} />} label="割増基礎" /></Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>キャンセル</Button>
          <Button variant="contained" onClick={handleSave}>保存</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

// --- Main Settings Page ---
const SettingsPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>設定</Typography>
      <Paper>
        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
          <Tab label="ユーザー管理" />
          <Tab label="手当種別" />
        </Tabs>
        <Box sx={{ p: 2 }}>
          <TabPanel value={tabValue} index={0}><UsersTab /></TabPanel>
          <TabPanel value={tabValue} index={1}><AllowanceTypesTab /></TabPanel>
        </Box>
      </Paper>
    </Box>
  );
};

export default SettingsPage;
