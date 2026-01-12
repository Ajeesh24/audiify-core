import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Lock, User, Eye, EyeOff, ArrowRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface AuthFormProps {
  onSuccess?: () => void;
  isDarkMode?: boolean;
}

export const AuthForm: React.FC<AuthFormProps> = ({ onSuccess, isDarkMode = true }) => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [isConfirmation, setIsConfirmation] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: '',
    confirmationCode: ''
  });

  const { signUp, signIn, confirmSignUp, resendSignUpCode } = useAuth();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const validateForm = () => {
    if (!formData.email || !formData.password) {
      setError('Email and password are required');
      return false;
    }

    if (isSignUp) {
      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match');
        return false;
      }
      if (formData.password.length < 8) {
        setError('Password must be at least 8 characters long');
        return false;
      }
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      if (isSignUp) {
        await signUp(formData.email, formData.password, {
          userAttributes: {
            name: formData.name || formData.email
          }
        });
        setIsConfirmation(true);
        setError('');
      } else {
        await signIn(formData.email, formData.password);
        onSuccess?.();
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.confirmationCode) {
      setError('Confirmation code is required');
      return;
    }

    setLoading(true);
    try {
      await confirmSignUp(formData.email, formData.confirmationCode);
      // Auto sign in after successful confirmation
      await signIn(formData.email, formData.password);
      onSuccess?.();
    } catch (err: any) {
      setError(err.message || 'Confirmation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    setLoading(true);
    try {
      await resendSignUpCode(formData.email);
      setError('Confirmation code sent to your email');
    } catch (err: any) {
      setError(err.message || 'Failed to resend code');
    } finally {
      setLoading(false);
    }
  };

  if (isConfirmation) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md mx-auto"
      >
        <div className={`
          relative rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl
          ${isDarkMode
            ? 'bg-slate-900/95 border border-slate-700/50'
            : 'bg-white/95 border border-slate-200'
          }
        `}>
          {/* Content */}
          <div className="relative z-10 p-6 sm:p-8">
            <h2 className={`
              text-xl sm:text-2xl font-bold text-center mb-2 font-['Inter']
              ${isDarkMode ? 'text-white' : 'text-slate-900'}
            `}>
              Verify Your Email
            </h2>
            <p className={`
              text-center mb-6 text-sm sm:text-base
              ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}
            `}>
              We sent a confirmation code to {formData.email}
            </p>

            <form onSubmit={handleConfirmation} className="space-y-4 sm:space-y-6">
              <div>
                <label className={`
                  block text-sm font-medium mb-2
                  ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}
                `}>
                  Confirmation Code
                </label>
                <input
                  type="text"
                  name="confirmationCode"
                  value={formData.confirmationCode}
                  onChange={handleInputChange}
                  placeholder="Enter 6-digit code"
                  className={`
                    w-full px-4 py-3 rounded-lg border transition-all touch-manipulation
                    ${isDarkMode
                      ? 'bg-slate-800/50 border-slate-700/50 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-white placeholder:text-slate-500'
                      : 'bg-slate-50 border-slate-300 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-slate-900 placeholder:text-slate-500'
                    }
                  `}
                  maxLength={6}
                />
              </div>

              {error && (
                <div className={`
                  text-sm p-3 rounded-lg border
                  ${isDarkMode
                    ? 'text-red-400 bg-red-500/10 border-red-500/20'
                    : 'text-red-600 bg-red-50 border-red-200'
                  }
                `}>
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-lg font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 touch-manipulation"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Verify & Sign In</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>

              <div className="text-center">
                <button
                  type="button"
                  onClick={handleResendCode}
                  className={`
                    text-sm transition-colors
                    ${isDarkMode
                      ? 'text-blue-400 hover:text-blue-300'
                      : 'text-blue-600 hover:text-blue-500'
                    }
                  `}
                  disabled={loading}
                >
                  Didn't receive the code? Resend
                </button>
              </div>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => setIsConfirmation(false)}
                  className={`
                    text-sm transition-colors
                    ${isDarkMode
                      ? 'text-slate-400 hover:text-slate-300'
                      : 'text-slate-600 hover:text-slate-500'
                    }
                  `}
                >
                  Back to sign up
                </button>
              </div>
            </form>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-md mx-auto"
    >
      <div className={`
        relative rounded-xl shadow-2xl overflow-hidden backdrop-blur-xl
        ${isDarkMode
          ? 'bg-slate-900/95 border border-slate-700/50'
          : 'bg-white/95 border border-slate-200'
        }
      `}>
        {/* Content */}
        <div className="relative z-10 p-6 sm:p-8">
          <h2 className={`
            text-xl sm:text-2xl font-bold text-center mb-2 font-['Inter']
            ${isDarkMode ? 'text-white' : 'text-slate-900'}
          `}>
            {isSignUp ? 'Create Account' : 'Welcome Back'}
          </h2>
          <p className={`
            text-center mb-6 text-sm sm:text-base
            ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}
          `}>
            {isSignUp
              ? 'Sign up to start converting articles to audio'
              : 'Sign in to access your audio library'
            }
          </p>

          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
            {isSignUp && (
              <div>
                <label className={`
                  block text-sm font-medium mb-2
                  ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}
                `}>
                  Name (optional)
                </label>
                <div className="relative">
                  <User className={`
                    absolute left-3 top-3 h-4 w-4 sm:h-5 sm:w-5
                    ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}
                  `} />
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Your name"
                    className={`
                      w-full pl-10 sm:pl-11 pr-4 py-3 rounded-lg border transition-all touch-manipulation
                      ${isDarkMode
                        ? 'bg-slate-800/50 border-slate-700/50 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-white placeholder:text-slate-500'
                        : 'bg-slate-50 border-slate-300 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-slate-900 placeholder:text-slate-500'
                      }
                    `}
                  />
                </div>
              </div>
            )}

            <div>
              <label className={`
                block text-sm font-medium mb-2
                ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}
              `}>
                Email
              </label>
              <div className="relative">
                <Mail className={`
                  absolute left-3 top-3 h-4 w-4 sm:h-5 sm:w-5
                  ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}
                `} />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="your@email.com"
                  className={`
                    w-full pl-10 sm:pl-11 pr-4 py-3 rounded-lg border transition-all touch-manipulation
                    ${isDarkMode
                      ? 'bg-slate-800/50 border-slate-700/50 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-white placeholder:text-slate-500'
                      : 'bg-slate-50 border-slate-300 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-slate-900 placeholder:text-slate-500'
                    }
                  `}
                  required
                />
              </div>
            </div>

            <div>
              <label className={`
                block text-sm font-medium mb-2
                ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}
              `}>
                Password
              </label>
              <div className="relative">
                <Lock className={`
                  absolute left-3 top-3 h-4 w-4 sm:h-5 sm:w-5
                  ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}
                `} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="••••••••"
                  className={`
                    w-full pl-10 sm:pl-11 pr-12 py-3 rounded-lg border transition-all touch-manipulation
                    ${isDarkMode
                      ? 'bg-slate-800/50 border-slate-700/50 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-white placeholder:text-slate-500'
                      : 'bg-slate-50 border-slate-300 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-slate-900 placeholder:text-slate-500'
                    }
                  `}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={`
                    absolute right-3 top-3 transition-colors touch-manipulation
                    ${isDarkMode
                      ? 'text-slate-500 hover:text-slate-300'
                      : 'text-slate-400 hover:text-slate-600'
                    }
                  `}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {isSignUp && (
              <div>
                <label className={`
                  block text-sm font-medium mb-2
                  ${isDarkMode ? 'text-slate-300' : 'text-slate-700'}
                `}>
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className={`
                    absolute left-3 top-3 h-4 w-4 sm:h-5 sm:w-5
                    ${isDarkMode ? 'text-slate-500' : 'text-slate-400'}
                  `} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    placeholder="••••••••"
                    className={`
                      w-full pl-10 sm:pl-11 pr-4 py-3 rounded-lg border transition-all touch-manipulation
                      ${isDarkMode
                        ? 'bg-slate-800/50 border-slate-700/50 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-white placeholder:text-slate-500'
                        : 'bg-slate-50 border-slate-300 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 text-slate-900 placeholder:text-slate-500'
                      }
                    `}
                    required
                  />
                </div>
              </div>
            )}

            {error && (
              <div className={`
                text-sm p-3 rounded-lg border
                ${isDarkMode
                  ? 'text-red-400 bg-red-500/10 border-red-500/20'
                  : 'text-red-600 bg-red-50 border-red-200'
                }
              `}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-lg font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 touch-manipulation shadow-lg shadow-blue-500/25"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <span>{isSignUp ? 'Create Account' : 'Sign In'}</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>

            <div className="text-center">
              <button
                type="button"
                onClick={() => setIsSignUp(!isSignUp)}
                className={`
                  text-sm transition-colors
                  ${isDarkMode
                    ? 'text-blue-400 hover:text-blue-300'
                    : 'text-blue-600 hover:text-blue-500'
                  }
                `}
              >
                {isSignUp
                  ? 'Already have an account? Sign in'
                  : "Don't have an account? Sign up"
                }
              </button>
            </div>

            {isSignUp && (
              <p className={`
                text-xs text-center leading-relaxed
                ${isDarkMode ? 'text-slate-500' : 'text-slate-500'}
              `}>
                By creating an account, you agree to our Terms of Service and Privacy Policy
              </p>
            )}
          </form>
        </div>
      </div>
    </motion.div>
  );
};