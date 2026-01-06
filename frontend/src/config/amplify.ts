// AWS Amplify configuration for Cognito authentication
// This configuration will be populated by environment variables during build/deployment

// Check if we have valid Cognito configuration
const hasValidCognitoConfig = () => {
  const userPoolId = (window as any).ENV?.VITE_COGNITO_USER_POOL_ID || import.meta.env.VITE_COGNITO_USER_POOL_ID;
  const clientId = (window as any).ENV?.VITE_COGNITO_CLIENT_ID || import.meta.env.VITE_COGNITO_CLIENT_ID;

  return !!(userPoolId && clientId && userPoolId !== '' && clientId !== '');
};

export const amplifyConfig = {
  Auth: {
    Cognito: {
      // These values will come from environment variables or runtime config
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID || '',
      identityPoolId: import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID || '',

      // AWS Region
      region: import.meta.env.VITE_COGNITO_REGION || 'ap-southeast-2',

      // Sign up configuration - simplified for email/password auth
      signUpVerificationMethod: 'code',

      // Basic login configuration - no OAuth complexity
      loginWith: {
        email: true,
        username: false,
      }
    }
  }
};

// Runtime configuration loader (checks window.ENV first)
export const getRuntimeAmplifyConfig = () => {
  // Check if runtime environment config is available (from env.js)
  if (typeof window !== 'undefined' && (window as any).ENV) {
    const env = (window as any).ENV;

    return {
      Auth: {
        Cognito: {
          userPoolId: env.VITE_COGNITO_USER_POOL_ID || amplifyConfig.Auth.Cognito.userPoolId,
          userPoolClientId: env.VITE_COGNITO_CLIENT_ID || amplifyConfig.Auth.Cognito.userPoolClientId,
          identityPoolId: env.VITE_COGNITO_IDENTITY_POOL_ID || amplifyConfig.Auth.Cognito.identityPoolId,
          region: env.VITE_COGNITO_REGION || amplifyConfig.Auth.Cognito.region,
          signUpVerificationMethod: amplifyConfig.Auth.Cognito.signUpVerificationMethod,
          loginWith: amplifyConfig.Auth.Cognito.loginWith
        }
      }
    };
  }

  return amplifyConfig;
};

// Check if Cognito is properly configured
export const isCognitoConfigured = hasValidCognitoConfig;

// Development mode configuration
export const isDevelopmentMode = () => {
  return !hasValidCognitoConfig() && (
    import.meta.env.DEV ||
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
  );
};