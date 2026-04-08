import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { View, ActivityIndicator } from 'react-native';
import { useAuthStore } from '../store/authStore';
import { RootStackParamList } from './types';

import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';
import HomeScreen from '../screens/HomeScreen';

// Placeholder screen for features not yet implemented
import PlaceholderScreen from '../screens/PlaceholderScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

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
      <Stack.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: '#1E293B' },
          headerTintColor: '#F8FAFC',
          headerTitleStyle: { fontWeight: '600' },
          contentStyle: { backgroundColor: '#0F172A' },
        }}
      >
        {!isAuthenticated ? (
          <>
            <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Register" component={RegisterScreen} options={{ title: 'Registro' }} />
          </>
        ) : (
          <>
            <Stack.Screen name="Home" component={HomeScreen} options={{ headerShown: false }} />
            <Stack.Screen name="Profile" component={PlaceholderScreen} options={{ title: 'Mi perfil' }} />
            <Stack.Screen name="Topics" component={PlaceholderScreen} options={{ title: 'Cuestionarios' }} />
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
