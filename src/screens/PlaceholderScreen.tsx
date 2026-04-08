import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function PlaceholderScreen({ route }: any) {
  return (
    <View style={styles.container}>
      <Text style={styles.emoji}>🚧</Text>
      <Text style={styles.text}>Próximamente</Text>
      <Text style={styles.sub}>Esta sección está en desarrollo</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0F172A',
  },
  emoji: { fontSize: 48, marginBottom: 16 },
  text: { fontSize: 20, fontWeight: '600', color: '#F8FAFC' },
  sub: { fontSize: 14, color: '#64748B', marginTop: 8 },
});
