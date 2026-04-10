import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  SafeAreaView, ActivityIndicator, Modal, Share,
} from 'react-native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import api from '../services/api';

type Props = { navigation: NativeStackNavigationProp<RootStackParamList, 'Journal'> };

interface Author { full_name: string; universidad?: string; }

interface Article {
  tema: string;
  date_str: string;
  issue_number?: number;
  authors: Author[];
  antecedentes: string;
  metodos: string;
  resultados: string;
  conclusiones: string;
}

const SUPERSCRIPTS = ['¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹', '¹⁰'];

function JournalCover({ article, mini = false }: { article: Article; mini?: boolean }) {
  const authors = (article.authors || []).slice(0, 10);
  const issueNumber = article.issue_number ?? 142;

  if (mini) {
    return (
      <View style={[c.cover, c.coverMini]}>
        <Text style={c.miniIssue}>Vol.148 | Issue {issueNumber}</Text>
        <Text style={c.miniSeal}>📜</Text>
        <Text style={c.miniJournalTitle}>The Journal of{'\n'}Residency Research</Text>
        <View style={c.miniDivider} />
        <Text style={c.miniArticleTitle} numberOfLines={3}>{article.tema}</Text>
      </View>
    );
  }

  return (
    <View style={c.cover}>
      {/* Header row */}
      <View style={c.headerRow}>
        <Text style={c.headerText}>Vol. 148  |  Issue {issueNumber}</Text>
        <Text style={c.headerText}>{article.date_str}</Text>
      </View>

      {/* Seal */}
      <View style={c.sealRow}>
        <View style={c.sealCircle}>
          <Text style={c.sealText}>JRR</Text>
        </View>
      </View>

      {/* Journal name */}
      <Text style={c.journalTitle}>
        <Text style={c.journalBold}>THE JOURNAL </Text>
        <Text style={c.journalItalic}>of </Text>
        <Text style={c.journalBold}>RESIDENCY RESEARCH</Text>
      </Text>
      <Text style={c.journalSubtitle}>For Clinical Residents and Beyond</Text>

      <View style={c.dividerThick} />
      <View style={c.dividerThin} />

      {/* Article title */}
      <Text style={c.articleTitle}>{article.tema}</Text>

      <View style={c.dividerMid} />

      {/* Authors */}
      {authors.length > 0 && (
        <>
          <Text style={c.authorsList}>
            {authors.map((a, i) => (
              <Text key={i}>
                {i > 0 ? ',  ' : ''}
                <Text style={c.authorName}>{a.full_name}</Text>
                <Text style={c.superscript}>{SUPERSCRIPTS[i]}</Text>
              </Text>
            ))}
          </Text>
          <Text style={c.affiliationsList}>
            {authors.map((a, i) => (
              <Text key={i}>
                {i > 0 ? '  ' : ''}
                <Text style={c.superscript}>{SUPERSCRIPTS[i]}</Text>
                {a.universidad || 'Independent Researcher'}{'  '}
              </Text>
            ))}
          </Text>
        </>
      )}

      {/* Abstract */}
      <Text style={c.abstractTitle}>ABSTRACT</Text>
      <Text style={c.abstractBody}><Text style={c.abstractLabel}>Antecedentes: </Text>{article.antecedentes}</Text>
      <Text style={c.abstractBody}><Text style={c.abstractLabel}>Métodos: </Text>{article.metodos}</Text>
      <Text style={c.abstractBody}><Text style={c.abstractLabel}>Resultados: </Text>{article.resultados}</Text>
      <Text style={c.abstractBody}><Text style={c.abstractLabel}>Conclusiones: </Text>{article.conclusiones}</Text>

      <View style={c.dividerMid} />
      <Text style={c.disclaimer}>
        Este artículo forma parte de la serie diaria de investigación. Los 10 residentes con mayor
        puntaje del día participan como autores. Este estudio es un ejercicio ficticio con fines de entretenimiento.
      </Text>
    </View>
  );
}

export default function JournalScreen({ navigation }: Props) {
  const [currentArticle, setCurrentArticle] = useState<Article | null>(null);
  const [history, setHistory] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [todayRes, historyRes] = await Promise.all([
          api.get('/api/journal/today'),
          api.get('/api/journal/history'),
        ]);
        setCurrentArticle(todayRes.data);
        setHistory(historyRes.data || []);
      } catch {}
      finally { setLoading(false); }
    })();
  }, []);

  const handleShare = async (article: Article) => {
    const text = [
      `📄 ${article.tema}`,
      `The Journal of Residency Research`,
      ``,
      `Antecedentes: ${article.antecedentes}`,
      `Métodos: ${article.metodos}`,
      `Resultados: ${article.resultados}`,
      `Conclusiones: ${article.conclusiones}`,
    ].join('\n');
    try {
      await Share.share({ message: text, title: 'Journal del Día' });
    } catch {}
  };

  if (loading) {
    return <View style={s.centered}><ActivityIndicator size="large" color="#6366F1" /></View>;
  }

  return (
    <SafeAreaView style={s.container}>
      <ScrollView contentContainerStyle={s.content} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={s.titleRow}>
          <Text style={s.sealEmoji}>📜</Text>
          <View>
            <Text style={s.title}>Journal del Día</Text>
            <Text style={s.subtitle}>Publicación diaria a las 9:00 PM</Text>
          </View>
        </View>
        <Text style={s.description}>
          Los 10 médicos con mayor puntaje en el Ranking del Día son seleccionados como autores del artículo publicado cada noche.
        </Text>

        {!currentArticle ? (
          <View style={s.empty}>
            <Text style={s.emptyText}>Aún no hay un journal publicado hoy.</Text>
          </View>
        ) : (
          <>
            {/* Action buttons */}
            <View style={s.actions}>
              <TouchableOpacity style={s.btnShare} onPress={() => handleShare(currentArticle)}>
                <Text style={s.btnShareText}>↑  Compartir</Text>
              </TouchableOpacity>
            </View>

            {/* Current journal */}
            <JournalCover article={currentArticle} />

            {/* History */}
            {history.length > 0 && (
              <>
                <Text style={s.historyTitle}>Ediciones anteriores</Text>
                <View style={s.historyGrid}>
                  {history.map((article, i) => (
                    <TouchableOpacity
                      key={i}
                      style={s.historyItem}
                      onPress={() => setSelectedArticle(article)}
                      activeOpacity={0.7}
                    >
                      <JournalCover article={article} mini />
                    </TouchableOpacity>
                  ))}
                </View>
              </>
            )}
          </>
        )}
      </ScrollView>

      {/* Modal for selected historical article */}
      <Modal visible={!!selectedArticle} transparent animationType="slide">
        <View style={s.modalOverlay}>
          <View style={s.modalContainer}>
            <View style={s.modalHeader}>
              <TouchableOpacity style={s.btnShare} onPress={() => selectedArticle && handleShare(selectedArticle)}>
                <Text style={s.btnShareText}>↑  Compartir</Text>
              </TouchableOpacity>
              <TouchableOpacity style={s.closeBtn} onPress={() => setSelectedArticle(null)}>
                <Text style={s.closeBtnText}>✕</Text>
              </TouchableOpacity>
            </View>
            <ScrollView>
              {selectedArticle && <JournalCover article={selectedArticle} />}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// Cover styles (parchment aesthetic)
const c = StyleSheet.create({
  cover: {
    backgroundColor: '#f0ede6',
    borderRadius: 4,
    padding: 24,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#c8c2b8',
  },
  coverMini: {
    padding: 6,
    marginBottom: 0,
  },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  headerText: { fontSize: 11, color: '#555', fontFamily: 'serif' },
  sealRow: { alignItems: 'center', marginBottom: 12 },
  sealCircle: {
    width: 64, height: 64, borderRadius: 32,
    borderWidth: 2, borderColor: '#4a3f2f',
    backgroundColor: '#e8e0d4',
    justifyContent: 'center', alignItems: 'center',
  },
  sealText: { fontSize: 14, fontWeight: 'bold', color: '#4a3f2f', fontFamily: 'serif' },
  journalTitle: { textAlign: 'center', marginBottom: 4 },
  journalBold: { fontSize: 18, fontWeight: 'bold', color: '#1a1a1a', fontFamily: 'serif', letterSpacing: 1 },
  journalItalic: { fontSize: 13, fontStyle: 'italic', color: '#1a1a1a', fontFamily: 'serif' },
  journalSubtitle: { fontSize: 10, color: '#555', textAlign: 'center', letterSpacing: 2, fontStyle: 'italic', fontFamily: 'serif', marginBottom: 10 },
  dividerThick: { height: 2, backgroundColor: '#4a3f2f', marginBottom: 2 },
  dividerThin: { height: 1, backgroundColor: '#7a6f5f', marginBottom: 14 },
  dividerMid: { height: 1, backgroundColor: '#b0a898', marginVertical: 12 },
  articleTitle: { fontSize: 18, fontWeight: 'bold', color: '#1a1a1a', textAlign: 'center', fontFamily: 'serif', lineHeight: 26, marginBottom: 10 },
  authorsList: { fontSize: 11, color: '#1a1a1a', textAlign: 'center', lineHeight: 20, marginBottom: 6, fontFamily: 'serif' },
  authorName: { fontWeight: 'bold', fontFamily: 'serif' },
  affiliationsList: { fontSize: 9, color: '#555', textAlign: 'center', lineHeight: 16, marginBottom: 12, fontFamily: 'serif' },
  superscript: { fontSize: 8, color: '#333' },
  abstractTitle: { fontSize: 13, fontWeight: 'bold', color: '#1a1a1a', textAlign: 'center', letterSpacing: 2, fontFamily: 'serif', marginBottom: 8 },
  abstractBody: { fontSize: 11, color: '#2a2a2a', lineHeight: 18, marginBottom: 6, fontFamily: 'serif' },
  abstractLabel: { fontWeight: 'bold', fontFamily: 'serif' },
  disclaimer: { fontSize: 9, color: '#777', fontStyle: 'italic', textAlign: 'center', lineHeight: 14, fontFamily: 'serif' },

  // Mini styles
  miniIssue: { fontSize: 6, color: '#555', fontFamily: 'serif', marginBottom: 3 },
  miniSeal: { fontSize: 14, textAlign: 'center', marginBottom: 3 },
  miniJournalTitle: { fontSize: 6, fontWeight: 'bold', color: '#1a1a1a', textAlign: 'center', fontFamily: 'serif', marginBottom: 3, lineHeight: 9 },
  miniDivider: { height: 1, backgroundColor: '#4a3f2f', marginBottom: 3 },
  miniArticleTitle: { fontSize: 6, fontWeight: 'bold', color: '#1a1a1a', textAlign: 'center', fontFamily: 'serif', lineHeight: 9 },
});

// Screen styles
const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F172A' },
  content: { padding: 20, paddingBottom: 40 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  sealEmoji: { fontSize: 36 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#F8FAFC' },
  subtitle: { fontSize: 12, color: '#64748B' },
  description: { fontSize: 13, color: '#94A3B8', lineHeight: 20, marginBottom: 20 },
  empty: { alignItems: 'center', paddingTop: 40 },
  emptyText: { color: '#64748B', fontSize: 15 },
  actions: { flexDirection: 'row', gap: 10, marginBottom: 16 },
  btnShare: { flex: 1, backgroundColor: '#6366F1', borderRadius: 10, paddingVertical: 11, alignItems: 'center' },
  btnShareText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  historyTitle: { fontSize: 16, fontWeight: 'bold', color: '#F8FAFC', marginBottom: 12 },
  historyGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  historyItem: {
    width: '30%',
    borderRadius: 4, borderWidth: 1, borderColor: '#334155', overflow: 'hidden',
  },
  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'flex-end' },
  modalContainer: { backgroundColor: '#0F172A', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '90%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  closeBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#334155', justifyContent: 'center', alignItems: 'center' },
  closeBtnText: { color: '#F8FAFC', fontSize: 16 },
});
