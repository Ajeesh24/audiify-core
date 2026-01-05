import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Amplify } from '@aws-amplify/core';
import {
  signUp,
  signIn,
  signOut,
  getCurrentUser,
  fetchAuthSession,
  confirmSignUp,
  resendSignUpCode,
  AuthUser,
  AuthTokens
} from '@aws-amplify/auth';
import { getRuntimeAmplifyConfig } from '../config/amplify';

// Configure Amplify
const config = getRuntimeAmplifyConfig();
Amplify.configure(config);

// Types
export interface User {
  userId: string;
  username: string;
  email: string;
  emailVerified: boolean;
  name?: string;
  picture?: string;
}

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  signUp: (email: string, password: string, options?: any) => Promise<any>;
  signIn: (email: string, password: string) => Promise<any>;
  signOut: () => Promise<void>;
  confirmSignUp: (email: string, code: string) => Promise<any>;
  resendSignUpCode: (email: string) => Promise<any>;
  getAccessToken: () => Promise<string | null>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const convertAuthUserToUser = (authUser: AuthUser): User => {
    return {
      userId: authUser.userId,
      username: authUser.username,
      email: authUser.signInDetails?.loginId || '',
      emailVerified: authUser.signInDetails?.authFlowType === 'USER_SRP_AUTH', // Simplified check
      name: undefined, // Will be populated from ID token if available
      picture: undefined
    };
  };

  const getAccessToken = async (): Promise<string | null> => {
    try {
      const session = await fetchAuthSession();
      return session.tokens?.accessToken?.toString() || null;
    } catch (error) {
      console.error('Failed to get access token:', error);
      return null;
    }
  };

  const refreshAuth = async () => {
    try {
      const authUser = await getCurrentUser();
      const convertedUser = convertAuthUserToUser(authUser);

      // Get additional user info from ID token if available
      try {
        const session = await fetchAuthSession();
        const idToken = session.tokens?.idToken?.payload;
        if (idToken) {
          convertedUser.email = idToken.email as string || convertedUser.email;
          convertedUser.emailVerified = idToken.email_verified as boolean || false;
          convertedUser.name = idToken.name as string;
          convertedUser.picture = idToken.picture as string;
        }
      } catch (tokenError) {
        console.warn('Failed to get ID token details:', tokenError);
      }

      setUser(convertedUser);
    } catch (error) {
      setUser(null);
      console.log('No authenticated user found');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshAuth();
  }, []);

  const handleSignUp = async (email: string, password: string, options?: any) => {
    try {
      const result = await signUp({
        username: email,
        password,
        options: {
          userAttributes: {
            email,
            ...options?.userAttributes
          },
          ...options
        }
      });
      return result;
    } catch (error) {
      console.error('Sign up failed:', error);
      throw error;
    }
  };

  const handleSignIn = async (email: string, password: string) => {
    try {
      const result = await signIn({
        username: email,
        password
      });

      if (result.isSignedIn) {
        await refreshAuth();
      }

      return result;
    } catch (error) {
      console.error('Sign in failed:', error);
      throw error;
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      setUser(null);
    } catch (error) {
      console.error('Sign out failed:', error);
      throw error;
    }
  };

  const handleConfirmSignUp = async (email: string, code: string) => {
    try {
      const result = await confirmSignUp({
        username: email,
        confirmationCode: code
      });
      return result;
    } catch (error) {
      console.error('Confirm sign up failed:', error);
      throw error;
    }
  };

  const handleResendSignUpCode = async (email: string) => {
    try {
      const result = await resendSignUpCode({
        username: email
      });
      return result;
    } catch (error) {
      console.error('Resend code failed:', error);
      throw error;
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    isAuthenticated: !!user,
    signUp: handleSignUp,
    signIn: handleSignIn,
    signOut: handleSignOut,
    confirmSignUp: handleConfirmSignUp,
    resendSignUpCode: handleResendSignUpCode,
    getAccessToken,
    refreshAuth
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};