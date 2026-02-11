/** 会社管理ページ - CRUD */

import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableContainer,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Paper,
  IconButton,
  Alert,
  Snackbar,
  CircularProgress,
  InputAdornment,
  MenuItem,
  Grid,
} from "@mui/material";
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
} from "@mui/icons-material";
import { useForm, Controller } from "react-hook-form";
import api from "@/services/api";

/* ---------- 型定義 ---------- */
interface Company {
  id: number;
  name: string;
  name_kana: string;
  address: string;
  phone: string;
  representative_name: string;
  closing_day: number;
  payment_day: number;
  payment_month_offset: number;
  health_insurance_prefecture: string;
  employment_business_type: string;
  created_at: string;
  updated_at: string;
}

type CompanyForm = Omit<Company, "id" | "created_at" | "updated_at">;

const PREFECTURES = [
  "北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県",
  "茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県",
  "新潟県","富山県","石川県","福井県","山梨県","長野県",
  "岐阜県","静岡県","愛知県","三重県",
  "滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県",
  "鳥取県","島根県","岡山県","広島県","山口県",
  "徳島県","香川県","愛媛県","高知県",
  "福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県",
];

const DAYS = Array.from({ length: 31 }, (_, i) => i + 1);

const defaultValues: CompanyForm = {
  name: "",
  name_kana: "",
  address: "",
  phone: "",
  representative_name: "",
  closing_day: 25,
  payment_day: 25,
  payment_month_offset: 1,
  health_insurance_prefecture: "東京都",
  employment_business_type: "一般",
};

/* ---------- コンポーネント ---------- */
export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Company | null>(null);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({ open: false, message: "", severity: "success" });

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CompanyForm>({ defaultValues });

  /* ---- データ取得 ---- */
  const fetchCompanies = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/companies", { params: search ? { search } : {} });
      setCompanies(res.data.items ?? res.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "取得に失敗しました";
      setSnackbar({ open: true, message: msg, severity: "error" });
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  /* ---- ダイアログ操作 ---- */
  const openCreateDialog = () => {
    setEditingId(null);
    reset(defaultValues);
    setDialogOpen(true);
  };

  const openEditDialog = (company: Company) => {
    setEditingId(company.id);
    reset({
      name: company.name,
      name_kana: company.name_kana,
      address: company.address,
      phone: company.phone,
      representative_name: company.representative_name,
      closing_day: company.closing_day,
      payment_day: company.payment_day,
      payment_month_offset: company.payment_month_offset,
      health_insurance_prefecture: company.health_insurance_prefecture,
      employment_business_type: company.employment_business_type,
    });
    setDialogOpen(true);
  };

  /* ---- 保存 ---- */
  const onSubmit = async (data: CompanyForm) => {
    try {
      if (editingId) {
        await api.put(`/companies/${editingId}`, data);
        setSnackbar({ open: true, message: "会社情報を更新しました", severity: "success" });
      } else {
        await api.post("/companies", data);
        setSnackbar({ open: true, message: "会社を登録しました", severity: "success" });
      }
      setDialogOpen(false);
      fetchCompanies();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "保存に失敗しました";
      setSnackbar({ open: true, message: msg, severity: "error" });
    }
  };

  /* ---- 削除 ---- */
  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/companies/${deleteTarget.id}`);
      setSnackbar({ open: true, message: "会社を削除しました", severity: "success" });
      setDeleteTarget(null);
      fetchCompanies();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "削除に失敗しました";
      setSnackbar({ open: true, message: msg, severity: "error" });
    }
  };

  /* ---- フィルタ ---- */
  const filtered = companies.filter(
    (c) =>
      c.name.includes(search) ||
      c.name_kana.includes(search) ||
      c.representative_name.includes(search)
  );

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4">会社管理</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog}>
          新規登録
        </Button>
      </Box>

      {/* 検索 */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <TextField
          size="small"
          placeholder="会社名で検索..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ width: 320 }}
        />
      </Paper>

      {/* テーブル */}
      <TableContainer component={Paper}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>会社名</TableCell>
                <TableCell>カナ</TableCell>
                <TableCell>代表者名</TableCell>
                <TableCell>電話番号</TableCell>
                <TableCell>締め日</TableCell>
                <TableCell>支払日</TableCell>
                <TableCell>都道府県</TableCell>
                <TableCell align="center">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center">
                    データがありません
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((c) => (
                  <TableRow key={c.id} hover>
                    <TableCell>{c.id}</TableCell>
                    <TableCell>{c.name}</TableCell>
                    <TableCell>{c.name_kana}</TableCell>
                    <TableCell>{c.representative_name}</TableCell>
                    <TableCell>{c.phone}</TableCell>
                    <TableCell>{c.closing_day}日</TableCell>
                    <TableCell>{c.payment_day}日</TableCell>
                    <TableCell>{c.health_insurance_prefecture}</TableCell>
                    <TableCell align="center">
                      <IconButton size="small" color="primary" onClick={() => openEditDialog(c)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => setDeleteTarget(c)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      {/* 登録・編集ダイアログ */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>{editingId ? "会社編集" : "会社登録"}</DialogTitle>
          <DialogContent dividers>
            <Grid container spacing={2} sx={{ mt: 0 }}>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="name"
                  control={control}
                  rules={{ required: "会社名は必須です" }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="会社名"
                      fullWidth
                      required
                      error={!!errors.name}
                      helperText={errors.name?.message}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="name_kana"
                  control={control}
                  rules={{ required: "カナは必須です" }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="会社名（カナ）"
                      fullWidth
                      required
                      error={!!errors.name_kana}
                      helperText={errors.name_kana?.message}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12}>
                <Controller
                  name="address"
                  control={control}
                  render={({ field }) => <TextField {...field} label="住所" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="phone"
                  control={control}
                  render={({ field }) => <TextField {...field} label="電話番号" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="representative_name"
                  control={control}
                  render={({ field }) => <TextField {...field} label="代表者名" fullWidth />}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="closing_day"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} label="締め日" select fullWidth>
                      {DAYS.map((d) => (
                        <MenuItem key={d} value={d}>
                          {d}日
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="payment_day"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} label="支払日" select fullWidth>
                      {DAYS.map((d) => (
                        <MenuItem key={d} value={d}>
                          {d}日
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <Controller
                  name="payment_month_offset"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} label="支払月オフセット" select fullWidth>
                      <MenuItem value={0}>当月</MenuItem>
                      <MenuItem value={1}>翌月</MenuItem>
                      <MenuItem value={2}>翌々月</MenuItem>
                    </TextField>
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="health_insurance_prefecture"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} label="健康保険 都道府県" select fullWidth>
                      {PREFECTURES.map((p) => (
                        <MenuItem key={p} value={p}>
                          {p}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="employment_business_type"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} label="雇用保険 事業種別" select fullWidth>
                      <MenuItem value="一般">一般</MenuItem>
                      <MenuItem value="農林水産">農林水産</MenuItem>
                      <MenuItem value="建設">建設</MenuItem>
                    </TextField>
                  )}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>キャンセル</Button>
            <Button type="submit" variant="contained" disabled={isSubmitting}>
              {isSubmitting ? <CircularProgress size={20} /> : "保存"}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* 削除確認 */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>削除確認</DialogTitle>
        <DialogContent>
          <Typography>
            「{deleteTarget?.name}」を削除してもよろしいですか？この操作は取り消せません。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>キャンセル</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>
            削除
          </Button>
        </DialogActions>
      </Dialog>

      {/* スナックバー */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
