import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Amplify } from 'aws-amplify';
import {
  signUp,
  signIn,
  signOut,
  getCurrentUser,
  fetchAuthSession,
  confirmSignUp,
  resendSignUpCode,
  type AuthUser
} from 'aws-amplify/auth';
import { getRuntimeAmplifyConfig, isCognitoConfigured, isDevelopmentMode } from '../config/amplify';

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
  isConfigured: boolean;
  isDevelopment: boolean;
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
  const [isConfigured, setIsConfigured] = useState(false);
  const [isDevelopment, setIsDevelopment] = useState(false);

  // Initialize Amplify configuration and check auth state
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const configured = isCognitoConfigured();
        const devMode = isDevelopmentMode();

        setIsConfigured(configured);
        setIsDevelopment(devMode);

        if (configured) {
          const config = getRuntimeAmplifyConfig();
          console.log('🔐 Initializing Amplify with Cognito configuration:', {
            userPoolId: config.Auth.Cognito.userPoolId,
            region: config.Auth.Cognito.region,
            configured: true
          });
          Amplify.configure(config);

          // Check for existing auth session after configuring Amplify
          await refreshAuth();
        } else {
          console.log('⚠️ Cognito not configured - running in development mode');
          setLoading(false);
        }
      } catch (error) {
        console.error('Failed to initialize Amplify:', error);
        setIsConfigured(false);
        setIsDevelopment(true);
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

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
    if (!isConfigured) {
      console.warn('Cognito not configured - cannot get access token');
      return null;
    }

    try {
      console.log('🔍 Fetching auth session...');
      const session = await fetchAuthSession();
      console.log('📋 Session object:', {
        tokens: !!session.tokens,
        accessToken: !!session.tokens?.accessToken,
        tokenString: session.tokens?.accessToken?.toString()?.substring(0, 50) + '...'
      });

      const token = session.tokens?.accessToken?.toString() || null;
      console.log('🎫 Access token retrieved:', token ? '✅ SUCCESS' : '❌ FAILED');
      return token;
    } catch (error) {
      console.error('❌ Failed to get access token:', error);
      return null;
    }
  };

  const refreshAuth = async () => {
    if (!isConfigured) {
      setLoading(false);
      return;
    }

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

  const handleSignUp = async (email: string, password: string, options?: any) => {
    if (!isConfigured) {
      throw new Error('Authentication not configured. Please deploy the infrastructure first.');
    }

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
    if (!isConfigured) {
      throw new Error('Authentication not configured. Please deploy the infrastructure first.');
    }

    try {
      const result = await signIn({
        username: email,
        password
      });

      // Refresh user data after sign in
      await refreshAuth();

      return result;
    } catch (error: any) {
      console.error('Sign in failed:', error);

      // Handle specific Amplify Auth errors
      if (error.name === 'UserAlreadyAuthenticatedError' ||
          error.message?.includes('There is already a signed in user')) {
        console.log('🔄 User already signed in, clearing session and retrying...');

        // Clear the existing session and retry
        await handleAuthError();

        // Wait a moment for cleanup to complete
        await new Promise(resolve => setTimeout(resolve, 500));

        // Retry the sign in
        try {
          const retryResult = await signIn({
            username: email,
            password
          });
          await refreshAuth();
          return retryResult;
        } catch (retryError) {
          console.error('Retry sign in also failed:', retryError);
          throw retryError;
        }
      }

      throw error;
    }
  };

  const handleSignOut = async () => {
    if (!isConfigured) {
      return; // Nothing to sign out from
    }

    try {
      // Force global sign out to clear all sessions
      await signOut({ global: true });

      // Clear local user state
      setUser(null);

      console.log('✅ User signed out successfully');
    } catch (error) {
      console.error('Sign out failed:', error);

      // Even if sign out fails, clear local state
      setUser(null);

      // Force clear any remaining auth state by reloading the page
      // This ensures complete session cleanup
      setTimeout(() => {
        window.location.reload();
      }, 100);
    }
  };

  // Add method to handle authentication errors (like expired tokens)
  const handleAuthError = async () => {
    console.log('🔄 Handling authentication error - clearing session');
    try {
      await signOut({ global: true });
    } catch (error) {
      console.warn('Failed to sign out during auth error handling:', error);
    }
    setUser(null);
  };

  const handleConfirmSignUp = async (email: string, confirmationCode: string) => {
    if (!isConfigured) {
      throw new Error('Authentication not configured. Please deploy the infrastructure first.');
    }

    try {
      const result = await confirmSignUp({
        username: email,
        confirmationCode
      });
      return result;
    } catch (error) {
      console.error('Confirm sign up failed:', error);
      throw error;
    }
  };

  const handleResendSignUpCode = async (email: string) => {
    if (!isConfigured) {
      throw new Error('Authentication not configured. Please deploy the infrastructure first.');
    }

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
    refreshAuth,
    isConfigured,
    isDevelopment,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};