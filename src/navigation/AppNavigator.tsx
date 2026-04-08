import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { View, ActivityIndicator } from 'react-native';
import { useAuthStore } from '../store/authStore';
import { RootStackParamList } from './types';

import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import HomeScreen from '../screens/HomeScreen';
import CuestionariosScreen from '../screens/CuestionariosScreen';
import SubmodulesScreen from '../screens/SubmodulesScreen';
import TopicsScreen from '../screens/TopicsScreen';
import QuizScreen from '../screens/QuizScreen';
import PlaceholderScreen from '../screens/PlaceholderScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

const screenOpts = {
  headerStyle: { backgroundColor: '#1E293B' },
  headerTintColor: '#F8FAFC',
  headerTitleStyle: { fontWeight: '600' as const },
  contentStyle: { backgroundColor: '#0F172A' },
};

export default function AppNavigator() {
  const { isAuthenticated, loadStoredAuth } = useAuthStore();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    loadStoredAuth().finally(() => setIsReady(true));
  }, []);

  if (!isReady) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F172A' }}>
        <ActivityIndicator size="large" color="#6366F1" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={screenOpts}>
        {!isAuthenticated ? (
          <>
            <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Register" component={RegisterScreen} options={{ title: 'Registro' }} />
          </>
        ) : (
          <>
            <Stack.Screen name="Home" component={HomeScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Profile" component={PlaceholderScreen} options={{ title: 'Mi perfil' }} />
            {/* Quiz flow */}
            <Stack.Screen name="Cuestionarios" component={CuestionariosScreen} options={{ title: 'Cuestionarios' }} />
            <Stack.Screen name="Submodules" component={SubmodulesScreen} options={({ route }) => ({ title: route.params.specialty })} />
            <Stack.Screen name="Topics" component={TopicsScreen} options={({ route }) => ({ title: route.params.submodule ?? route.params.specialty })} />
            <Stack.Screen name="Quiz" component={QuizScreen} options={{ title: 'Cuestionario', headerBackTitle: 'Temas' }} />
            {/* Phase 3+ */}
            <Stack.Screen name="Flashcards" component={PlaceholderScreen} options={{ title: 'Flashcards' }} />
            <Stack.Screen name="Simulacros" component={PlaceholderScreen} options={{ title: 'Simulacros' }} />
            <Stack.Screen name="Duels" component={PlaceholderScreen} options={{ title: 'Duelos' }} />
            <Stack.Screen name="ImagenDX" component={PlaceholderScreen} options={{ title: 'ImagenDX' }} />
            <Stack.Screen name="Planner" component={PlaceholderScreen} options={{ title: 'Planificador' }} />
            <Stack.Screen name="Perlas" component={PlaceholderScreen} options={{ title: 'Perlas Diarias' }} />
            <Stack.Screen name="Presentaciones" component={PlaceholderScreen} options={{ title: 'Presentaciones' }} />
            <Stack.Screen name="Leaderboard" component={PlaceholderScreen} options={{ title: 'Ranking' }} />
            <Stack.Screen name="CaminoDelMedico" component={PlaceholderScreen} options={{ title: 'Camino del Médico' }} />
            <Stack.Screen name="Journal" component={PlaceholderScreen} options={{ title: 'Journal del Día' }} />
            <Stack.Screen name="Support" component={PlaceholderScreen} options={{ title: 'Soporte' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
