import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { KnowledgeEntryItem, EntityItem, PatrolUserItem, AuditLogItem } from '../types';
import {
  Database,
  Search,
  Plus,
  Merge,
  CheckCircle,
  FileDown,
  Layers,
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  AlertCircle,
  RefreshCw,
  Users,
  FileText,
  UserCheck,
  UserX,
  Lock,
} from 'lucide-react';

export const CurationPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'knowledge' | 'entities' | 'patrol_users' | 'audit'>('knowledge');

  // Status message
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // 1. Knowledge Base State
  const [knowledgeList, setKnowledgeList] = useState<KnowledgeEntryItem[]>([]);
  const [loadingKnowledge, setLoadingKnowledge] = useState<boolean>(true);
  const [knowledgeSearch, setKnowledgeSearch] = useState<string>('');
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [newEntry, setNewEntry] = useState({
    ticket_number: '',
    content_text: '',
    verified_category: 'HOAKS',
    verified_risk: 'SEDANG',
    analyst_decision: 'VALIDATED',
    analyst_notes: '',
  });

  // 2. Entities State
  const [entityList, setEntityList] = useState<EntityItem[]>([]);
  const [loadingEntities, setLoadingEntities] = useState<boolean>(true);
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('TOPIC');
  const [showMergeModal, setShowMergeModal] = useState<boolean>(false);
  const [mergeSourceId, setMergeSourceId] = useState<string>('');
  const [mergeTargetId, setMergeTargetId] = useState<string>('');

  // 3. Patrol Users State
  const [patrolUsers, setPatrolUsers] = useState<PatrolUserItem[]>([]);
  const [loadingPatrolUsers, setLoadingPatrolUsers] = useState<boolean>(false);
  const [showAddUserModal, setShowAddUserModal] = useState<boolean>(false);
  const [newUser, setNewUser] = useState({
    telegram_id: '',
    full_name: '',
    role: 'OPERATOR',
  });

  // 4. Audit Logs State
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loadingAudit, setLoadingAudit] = useState<boolean>(false);

  // Export State
  const [exporting, setExporting] = useState<boolean>(false);

  const fetchKnowledge = async () => {
    try {
      setLoadingKnowledge(true);
      const res = await apiClient.admin.listKnowledge({ search: knowledgeSearch, limit: 50 });
      setKnowledgeList(res.items || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingKnowledge(false);
    }
  };

  const fetchEntities = async () => {
    try {
      setLoadingEntities(true);
      const res = await apiClient.admin.listEntities({ entity_type: entityTypeFilter, limit: 50 });
      setEntityList(res.items || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingEntities(false);
    }
  };

  const fetchPatrolUsers = async () => {
    try {
      setLoadingPatrolUsers(true);
      const data = await apiClient.admin.listPatrolUsers();
      setPatrolUsers(data || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingPatrolUsers(false);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      setLoadingAudit(true);
      const res = await apiClient.admin.listAudit({ limit: 50 });
      setAuditLogs(res.items || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'knowledge') {
      fetchKnowledge();
    } else if (activeTab === 'entities') {
      fetchEntities();
    } else if (activeTab === 'patrol_users') {
      fetchPatrolUsers();
    } else if (activeTab === 'audit') {
      fetchAuditLogs();
    }
  }, [activeTab, entityTypeFilter]);

  // Handle Deactivate Knowledge Base Entry (Soft-delete NFR-07)
  const handleDeactivateKnowledge = async (entryId: string) => {
    if (!window.confirm('Yakin ingin menonaktifkan entri preseden RAG ini? Entri tidak dihapus secara fisik (NFR-07) melainkan dinonaktifkan logis.')) {
      return;
    }
    try {
      await apiClient.admin.deleteKnowledge(entryId);
      setStatusMsg({ text: 'Entri Knowledge Base berhasil dinonaktifkan (is_active = False)!', type: 'success' });
      fetchKnowledge();
    } catch (err: any) {
      setStatusMsg({ text: 'Gagal menonaktifkan entri preseden RAG', type: 'error' });
    }
  };

  const handleCreateKnowledge = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.admin.createKnowledge(newEntry);
      setShowAddModal(false);
      setNewEntry({
        ticket_number: '',
        content_text: '',
        verified_category: 'HOAKS',
        verified_risk: 'SEDANG',
        analyst_decision: 'VALIDATED',
        analyst_notes: '',
      });
      setStatusMsg({ text: 'Entri knowledge base berhasil ditambahkan dan di-embed ke RAG!', type: 'success' });
      fetchKnowledge();
    } catch (err: any) {
      setStatusMsg({ text: 'Gagal menambahkan entri RAG', type: 'error' });
    }
  };

  const handleApproveEntity = async (entityId: string) => {
    try {
      await apiClient.admin.approveEntity(entityId);
      setStatusMsg({ text: 'Entitas berhasil disetujui (APPROVED)!', type: 'success' });
      fetchEntities();
    } catch (err: any) {
      setStatusMsg({ text: 'Gagal menyetujui entitas', type: 'error' });
    }
  };

  const handleMergeEntities = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mergeSourceId || !mergeTargetId) return;
    try {
      await apiClient.admin.mergeEntities(mergeSourceId, mergeTargetId);
      setShowMergeModal(false);
      setMergeSourceId('');
      setMergeTargetId('');
      setStatusMsg({ text: 'Entitas duplikat berhasil dimerge ke entitas kanonikal!', type: 'success' });
      fetchEntities();
    } catch (err: any) {
      setStatusMsg({ text: 'Gagal melakukan merge entitas', type: 'error' });
    }
  };

  const handleAddPatrolUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUser.telegram_id || !newUser.full_name) return;
    try {
      await apiClient.admin.createOrUpdatePatrolUser({
        telegram_id: parseInt(newUser.telegram_id, 10),
        full_name: newUser.full_name,
        role: newUser.role,
      });
      setShowAddUserModal(false);
      setNewUser({ telegram_id: '', full_name: '', role: 'OPERATOR' });
      setStatusMsg({ text: 'Pengguna patroli Telegram berhasil didaftarkan!', type: 'success' });
      fetchPatrolUsers();
    } catch (err: any) {
      setStatusMsg({ text: 'Gagal mendaftarkan pengguna patroli Telegram', type: 'error' });
    }
  };

  const handleTogglePatrolUser = async (userItem: PatrolUserItem) => {
    try {
      await apiClient.admin.updatePatrolUser(userItem.id, {
        is_active: !userItem.is_active,
      });
      setStatusMsg({
        text: `Pengguna ${userItem.full_name} berhasil ${!userItem.is_active ? 'diaktifkan' : 'dinonaktifkan'}!`,
        type: 'success',
      });
      fetchPatrolUsers();
    } catch (err: any) {
      setStatusMsg({ text: 'Gagal mengubah status pengguna patroli', type: 'error' });
    }
  };

  const handleExportCSV = async () => {
    try {
      setExporting(true);
      await apiClient.v1.exportBlob('csv');
      setStatusMsg({ text: 'Ekspor CSV rekap berhasil diunduh secara aman via Bearer Token!', type: 'success' });
    } catch (err: any) {
      setStatusMsg({ text: 'Gagal mengekspor data CSV', type: 'error' });
    } finally {
      setExporting(false);
    }
  };

  // RBAC Lock Screen for Non-Admin
  if (user && user.role !== 'ADMIN') {
    return (
      <div className="cyber-card rounded-2xl p-12 text-center max-w-lg mx-auto space-y-4 my-12 border-rose-500/30 shadow-2xl shadow-rose-950/20">
        <div className="w-16 h-16 rounded-full bg-rose-950/60 border border-rose-800 flex items-center justify-center mx-auto text-rose-400">
          <Lock className="w-8 h-8" />
        </div>
        <h2 className="text-lg font-bold text-white tracking-wide uppercase font-mono">
          Akses Terbatas: Khusus Administrator
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          Akun Anda saat ini memiliki peran <span className="font-mono text-cyan-400 font-bold">{user.role}</span> (Read-Only). Halaman Pusat Kurasi, Manajemen Whitelist Bot Telegram, dan Pengaturan Knowledge Base RAG dilindungi oleh kebijakan keamanan RBAC (NFR-05) dan hanya dapat diakses oleh Administrator.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            Pusat Kurasi RAG & Tata Kelola Administrasi (Admin)
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Kelola data preseden RAG, normalisasi entitas 3 pilar, whitelist bot Telegram, dan audit log forensik.
          </p>
        </div>

        {/* Secure Export Button */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            disabled={exporting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-800/40 text-xs font-semibold transition-colors disabled:opacity-50"
          >
            <FileDown className="w-3.5 h-3.5" />
            <span>{exporting ? 'Mengunduh...' : 'Ekspor CSV Rekap (Aman)'}</span>
          </button>
        </div>
      </div>

      {statusMsg && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center justify-between ${
            statusMsg.type === 'success'
              ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
              : 'bg-rose-950/80 text-rose-300 border border-rose-800'
          }`}
        >
          <span>{statusMsg.text}</span>
          <button onClick={() => setStatusMsg(null)} className="text-slate-400 hover:text-white font-bold ml-4">
            ×
          </button>
        </div>
      )}

      {/* 4 Tabs Nav */}
      <div className="flex border-b border-slate-800 gap-4 overflow-x-auto pb-0.5">
        <button
          onClick={() => setActiveTab('knowledge')}
          className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'knowledge'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          RAG Knowledge Base ({knowledgeList.length})
        </button>

        <button
          onClick={() => setActiveTab('entities')}
          className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'entities'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          Normalisasi Entitas ({entityList.length})
        </button>

        <button
          onClick={() => setActiveTab('patrol_users')}
          className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'patrol_users'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-4 h-4" />
          Whitelist Bot Telegram ({patrolUsers.length})
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`pb-3 text-xs font-semibold flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'audit'
              ? 'border-cyan-400 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          Jejak Audit Forensik ({auditLogs.length})
        </button>
      </div>

      {/* ── TAB 1: RAG KNOWLEDGE BASE ── */}
      {activeTab === 'knowledge' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Cari tiket, teks konten, catatan..."
                value={knowledgeSearch}
                onChange={(e) => setKnowledgeSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchKnowledge()}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                onClick={fetchKnowledge}
                className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
                title="Refresh"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Tambah Kasus Latih</span>
              </button>
            </div>
          </div>

          <div className="cyber-card rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Tiket</th>
                    <th className="py-3 px-4">Ringkasan Konten</th>
                    <th className="py-3 px-4">Kategori Validasi</th>
                    <th className="py-3 px-4">Risiko</th>
                    <th className="py-3 px-4">Keputusan Analis</th>
                    <th className="py-3 px-4">Catatan Analis</th>
                    <th className="py-3 px-4 text-center">Status RAG</th>
                    <th className="py-3 px-4 text-center">Vektor RAG</th>
                    <th className="py-3 px-4 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {loadingKnowledge ? (
                    <tr>
                      <td colSpan={9} className="text-center py-8 text-slate-500 font-mono">
                        Memuat entri knowledge base...
                      </td>
                    </tr>
                  ) : knowledgeList.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="text-center py-8 text-slate-500 font-mono">
                        Belum ada entri knowledge base. Keputusan analis akan otomatis tersimpan ke sini saat divalidasi.
                      </td>
                    </tr>
                  ) : (
                    knowledgeList.map((k) => (
                      <tr key={k.entry_id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-mono text-cyan-300 font-semibold">{k.ticket_number}</td>
                        <td className="py-3 px-4 max-w-xs text-slate-300 truncate">{k.content_summary}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800">
                            {k.verified_category}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-200">{k.verified_risk || '-'}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] ${
                              k.analyst_decision === 'VALIDATED' || k.analyst_decision === 'APPROVED'
                                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                : k.analyst_decision === 'MODIFIED'
                                ? 'bg-amber-950 text-amber-300 border border-amber-800'
                                : 'bg-rose-950 text-rose-300 border border-rose-800'
                            }`}
                          >
                            {k.analyst_decision}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-400 italic max-w-xs truncate">
                          {k.analyst_notes || '-'}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {k.is_active ? (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono font-bold">
                              AKTIF
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                              NONAKTIF
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {k.has_embedding ? (
                            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-mono bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/50">
                              <ShieldCheck className="w-3 h-3" />
                              768-dim
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-500 font-mono">-</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {k.is_active && (
                            <button
                              onClick={() => handleDeactivateKnowledge(k.entry_id)}
                              className="px-2.5 py-1 rounded bg-rose-950/80 hover:bg-rose-900/80 text-rose-300 border border-rose-800/60 text-[10px] font-semibold transition-colors"
                              title="Nonaktifkan logis (NFR-07)"
                            >
                              Nonaktifkan
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: ENTITIES NORMALIZATION ── */}
      {activeTab === 'entities' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
              {(['TOPIC', 'ACTOR', 'SOURCE'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setEntityTypeFilter(t)}
                  className={`px-3 py-1 rounded font-medium transition-colors ${
                    entityTypeFilter === t
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {t === 'TOPIC' ? 'Topik Isu' : t === 'ACTOR' ? 'Aktor Sasaran' : 'Sumber Konten'}
                </button>
              ))}
            </div>

            <button
              onClick={() => setShowMergeModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm"
            >
              <Merge className="w-3.5 h-3.5" />
              <span>Merge Entitas Duplikat</span>
            </button>
          </div>

          <div className="cyber-card rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Nama Kanonikal</th>
                    <th className="py-3 px-4">Tipe Entitas</th>
                    <th className="py-3 px-4">Kategori / Sektor</th>
                    <th className="py-3 px-4">Alias Terdaftar</th>
                    <th className="py-3 px-4">Status Kurasi</th>
                    <th className="py-3 px-4 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {loadingEntities ? (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-500 font-mono">
                        Memuat daftar entitas...
                      </td>
                    </tr>
                  ) : entityList.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-500 font-mono">
                        Belum ada entitas untuk tipe ini. Sistem akan mendaftarkan temuan entitas patroli secara otomatis.
                      </td>
                    </tr>
                  ) : (
                    entityList.map((ent) => (
                      <tr key={ent.entity_id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-semibold text-white">{ent.canonical_name}</td>
                        <td className="py-3 px-4 font-mono text-cyan-400">{ent.entity_type}</td>
                        <td className="py-3 px-4 text-slate-300">{ent.category || '-'}</td>
                        <td className="py-3 px-4 max-w-xs">
                          <div className="flex flex-wrap gap-1">
                            {ent.aliases && ent.aliases.length > 0 ? (
                              ent.aliases.slice(0, 4).map((al, idx) => (
                                <span
                                  key={idx}
                                  className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono border border-slate-700"
                                >
                                  {al}
                                </span>
                              ))
                            ) : (
                              <span className="text-slate-500 text-[10px] italic">Tidak ada alias</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] ${
                              ent.status === 'APPROVED'
                                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                : ent.status === 'PENDING_REVIEW'
                                ? 'bg-amber-950 text-amber-300 border border-amber-800'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {ent.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          {ent.status === 'PENDING_REVIEW' && (
                            <button
                              onClick={() => handleApproveEntity(ent.entity_id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 text-[11px] font-semibold transition-colors"
                            >
                              <CheckCircle className="w-3 h-3" />
                              Approve
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 3: PATROL USERS (WHITELIST TELEGRAM) ── */}
      {activeTab === 'patrol_users' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-cyan-400" />
                Daftar Whitelist Pengguna Bot Telegram
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Kelola hak otorisasi piket patroli untuk 3 peran: OPERATOR, ANALYST, dan ADMIN.
              </p>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                onClick={fetchPatrolUsers}
                className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
                title="Refresh"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setShowAddUserModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Tambah Pengguna Bot</span>
              </button>
            </div>
          </div>

          <div className="cyber-card rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Telegram ID</th>
                    <th className="py-3 px-4">Nama Lengkap</th>
                    <th className="py-3 px-4">Username Telegram</th>
                    <th className="py-3 px-4">Peran (Role)</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {loadingPatrolUsers ? (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-500 font-mono">
                        Memuat daftar pengguna Telegram...
                      </td>
                    </tr>
                  ) : patrolUsers.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-500 font-mono">
                        Belum ada pengguna terdaftar pada whitelist bot Telegram.
                      </td>
                    </tr>
                  ) : (
                    patrolUsers.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-mono text-cyan-300 font-bold">{u.telegram_id}</td>
                        <td className="py-3 px-4 font-semibold text-white">{u.full_name || 'Tanpa Nama'}</td>
                        <td className="py-3 px-4 text-slate-400 font-mono">@{u.username || 'anonim'}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              u.role === 'ADMIN'
                                ? 'bg-rose-950 text-rose-300 border border-rose-800'
                                : u.role === 'ANALYST'
                                ? 'bg-amber-950 text-amber-300 border border-amber-800'
                                : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                            }`}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          {u.is_active ? (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                              AKTIF
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">
                              NONAKTIF
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleTogglePatrolUser(u)}
                            className={`px-2.5 py-1 rounded text-[10px] font-semibold border transition-colors ${
                              u.is_active
                                ? 'bg-rose-950/70 text-rose-300 border-rose-800/50 hover:bg-rose-900/80'
                                : 'bg-emerald-950/70 text-emerald-300 border-emerald-800/50 hover:bg-emerald-900/80'
                            }`}
                          >
                            {u.is_active ? 'Nonaktifkan' : 'Aktifkan'}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 4: AUDIT LOGS (FORENSIK) ── */}
      {activeTab === 'audit' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                Catatan Jejak Audit Forensik Sistem
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Rekaman aktivitas sistem, validasi analis, integrasi scraper, dan mutasi knowledge base (Immutable).
              </p>
            </div>
            <button
              onClick={fetchAuditLogs}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
              title="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="cyber-card rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] font-semibold tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Waktu</th>
                    <th className="py-3 px-4">Aktor Pengguna</th>
                    <th className="py-3 px-4">Aksi Forensik</th>
                    <th className="py-3 px-4">Entitas Target</th>
                    <th className="py-3 px-4">Detail Kejadian</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {loadingAudit ? (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-slate-500 font-mono">
                        Memuat jejak audit...
                      </td>
                    </tr>
                  ) : auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-slate-500 font-mono">
                        Belum ada jejak audit tercatat.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-mono text-slate-400 text-[11px] whitespace-nowrap">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString('id-ID') : '-'}
                        </td>
                        <td className="py-3 px-4 font-semibold text-cyan-300">
                          {log.actor_username || 'system'}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-900 text-slate-200 border border-slate-700 font-mono font-bold">
                            {log.action}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">
                          {log.entity_type}: {log.entity_id}
                        </td>
                        <td className="py-3 px-4 text-slate-400 max-w-sm truncate text-[11px]">
                          {typeof log.details === 'object' ? JSON.stringify(log.details) : String(log.details || '-')}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Modal Tambah Kasus Manual */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0b1329] border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Plus className="w-4 h-4 text-cyan-400" />
              Tambah Kasus Latih RAG Manual
            </h3>
            <form onSubmit={handleCreateKnowledge} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Nomor Tiket / Referensi</label>
                <input
                  type="text"
                  required
                  placeholder="PS-20261023-REF1"
                  value={newEntry.ticket_number}
                  onChange={(e) => setNewEntry({ ...newEntry, ticket_number: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Teks Konten / Narasi</label>
                <textarea
                  required
                  rows={3}
                  placeholder="Kutipan konten narasi temuan yang akan di-embed..."
                  value={newEntry.content_text}
                  onChange={(e) => setNewEntry({ ...newEntry, content_text: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Kategori Validasi</label>
                  <select
                    value={newEntry.verified_category}
                    onChange={(e) => setNewEntry({ ...newEntry, verified_category: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white"
                  >
                    <option value="HOAKS">HOAKS</option>
                    <option value="DI_LUAR_KONTEKS">DI_LUAR_KONTEKS</option>
                    <option value="UJARAN_KEBENCIAN">UJARAN_KEBENCIAN</option>
                    <option value="PROVOKASI_SARA">PROVOKASI_SARA</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Tingkat Risiko</label>
                  <select
                    value={newEntry.verified_risk}
                    onChange={(e) => setNewEntry({ ...newEntry, verified_risk: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white"
                  >
                    <option value="TINGGI">TINGGI</option>
                    <option value="SEDANG">SEDANG</option>
                    <option value="RENDAH">RENDAH</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Catatan Analis</label>
                <input
                  type="text"
                  placeholder="Alasan klasifikasi / pedoman preseden..."
                  value={newEntry.analyst_notes}
                  onChange={(e) => setNewEntry({ ...newEntry, analyst_notes: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 text-xs font-medium"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold"
                >
                  Simpan & Embed
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Merge Entitas */}
      {showMergeModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0b1329] border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Merge className="w-4 h-4 text-indigo-400" />
              Merge Entitas Duplikat
            </h3>
            <p className="text-xs text-slate-400">
              Gabungkan entitas sumber (duplikat) ke entitas target kanonikal. Nama sumber akan otomatis didaftarkan sebagai alias target.
            </p>
            <form onSubmit={handleMergeEntities} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">ID Entitas Sumber (Akan Digabung)</label>
                <input
                  type="text"
                  required
                  placeholder="UUID Entitas Sumber"
                  value={mergeSourceId}
                  onChange={(e) => setMergeSourceId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white font-mono"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">ID Entitas Target (Kanonikal Utama)</label>
                <input
                  type="text"
                  required
                  placeholder="UUID Entitas Target"
                  value={mergeTargetId}
                  onChange={(e) => setMergeTargetId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white font-mono"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowMergeModal(false)}
                  className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 text-xs font-medium"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
                >
                  Eksekusi Merge
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Tambah Pengguna Patroli Telegram */}
      {showAddUserModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="bg-[#0b1329] border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-400" />
              Tambah Pengguna Bot Telegram
            </h3>
            <form onSubmit={handleAddPatrolUser} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Telegram User ID (Angka)</label>
                <input
                  type="number"
                  required
                  placeholder="Contoh: 123456789"
                  value={newUser.telegram_id}
                  onChange={(e) => setNewUser({ ...newUser, telegram_id: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white font-mono"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Nama Lengkap Petugas</label>
                <input
                  type="text"
                  required
                  placeholder="Nama Lengkap Analis / Operator"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Peran Akses (Role)</label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-xs text-white"
                >
                  <option value="OPERATOR">OPERATOR (Kirim Tautan/Foto & Cek Status)</option>
                  <option value="ANALYST">ANALYST (Hak Operator + Validasi HITL & Rekap DOCX)</option>
                  <option value="ADMIN">ADMIN (Hak Analyst + Kelola Whitelist Pengguna)</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddUserModal(false)}
                  className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 text-xs font-medium"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold"
                >
                  Daftarkan Whitelist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
