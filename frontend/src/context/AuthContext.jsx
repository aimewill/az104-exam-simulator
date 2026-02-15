import { createContext, useContext, useState, useEffect } from 'react';
import { authApi, setToken, removeToken, getToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const userData = await authApi.me();
          setUser(userData);
        } catch (err) {
          // Token invalid or expired
          removeToken();
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  const login = async (email, password) => {
    const response = await authApi.login(email, password);
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  };

  const register = async (email, password, displayName = null) => {
    const response = await authApi.register(email, password, displayName);
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  };

  const logout = () => {
    removeToken();
    setUser(null);
  };

  const value = {
    user,
    isAuthenticated: !!user,
    loading,
    login,
    register,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
