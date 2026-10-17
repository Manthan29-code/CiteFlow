import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { User } from '@/types/api';
import { getMe, login, logout, register, AuthCredentials } from '@/api/auth';
import { getErrorMessage } from '@/api/errors';

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isCheckingSession: boolean;
  isLoading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  isCheckingSession: true,
  isLoading: false,
  error: null,
};

export const checkAuthSession = createAsyncThunk('auth/checkAuthSession', async (_, { rejectWithValue }) => {
  try {
    const user = await getMe();
    return user;
  } catch (error) {
    return rejectWithValue(getErrorMessage(error));
  }
});

export const loginUser = createAsyncThunk('auth/loginUser', async (credentials: AuthCredentials, { rejectWithValue }) => {
  try {
    const user = await login(credentials);
    return user;
  } catch (error) {
    return rejectWithValue(getErrorMessage(error));
  }
});

export const registerUser = createAsyncThunk('auth/registerUser', async (credentials: AuthCredentials, { rejectWithValue }) => {
  try {
    const user = await register(credentials);
    return user;
  } catch (error) {
    return rejectWithValue(getErrorMessage(error));
  }
});

export const logoutUser = createAsyncThunk('auth/logoutUser', async (_, { rejectWithValue }) => {
  try {
    await logout();
    return null;
  } catch (error) {
    return rejectWithValue(getErrorMessage(error));
  }
});

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearAuthError(state) {
      state.error = null;
    },
    setUser(state, action: PayloadAction<User | null>) {
      state.user = action.payload;
      state.isAuthenticated = !!action.payload;
    },
  },
  extraReducers: (builder) => {
    // checkAuthSession
    builder
      .addCase(checkAuthSession.pending, (state) => {
        state.isCheckingSession = true;
      })
      .addCase(checkAuthSession.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
        state.isCheckingSession = false;
        state.error = null;
      })
      .addCase(checkAuthSession.rejected, (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.isCheckingSession = false;
      });

    // loginUser
    builder
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
        state.isLoading = false;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = (action.payload as string) || 'Login failed';
      });

    // registerUser
    builder
      .addCase(registerUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(registerUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
        state.isLoading = false;
        state.error = null;
      })
      .addCase(registerUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = (action.payload as string) || 'Registration failed';
      });

    // logoutUser
    builder
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.isLoading = false;
        state.error = null;
      })
      .addCase(logoutUser.rejected, (state) => {
        state.user = null;
        state.isAuthenticated = false;
        state.isLoading = false;
      });
  },
});

export const { clearAuthError, setUser } = authSlice.actions;
export default authSlice.reducer;
