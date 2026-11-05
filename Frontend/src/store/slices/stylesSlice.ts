import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import {
  listCitationStyles,
  getCitationStyleFields,
  createCitationStyle,
  updateCitationStyle,
  deleteCitationStyle,
} from '@/api/citationStyles';
import {
  CitationStyle,
  CreateCitationStyleRequest,
  UpdateCitationStyleRequest,
} from '@/types/api';

export interface StylesState {
  styles: CitationStyle[];
  selectedStyleId: string | null;
  allowedFields: string[];
  isLoading: boolean;
  error: string | null;
}

const initialState: StylesState = {
  styles: [],
  selectedStyleId: null,
  allowedFields: [
    'CITATION_KEY',
    'KEY',
    'AUTHORS',
    'AUTHORS_LAST_FIRST(.)',
    'AUTHORS_LAST_FIRST()',
    'AUTHORS_FIRST(.)_LAST',
    'AUTHORS_FIRST()_LAST',
    'TITLE',
    'JOURNAL',
    'JOURNAL_ABBREVIATION',
    'YEAR',
    'VOLUME',
    'ISSUE',
    'FIRST_PAGE',
    'ARTICLE_NUMBER',
    'LOCATOR',
    'DOI',
    'DOI_URL',
  ],
  isLoading: false,
  error: null,
};

export const fetchStyles = createAsyncThunk<CitationStyle[]>(
  'styles/fetchStyles',
  async (_, { rejectWithValue }) => {
    try {
      return await listCitationStyles();
    } catch (err: unknown) {
      return rejectWithValue(err instanceof Error ? err.message : 'Failed to fetch citation styles');
    }
  }
);

export const fetchAllowedFields = createAsyncThunk<string[]>(
  'styles/fetchAllowedFields',
  async (_, { rejectWithValue }) => {
    try {
      return await getCitationStyleFields();
    } catch (err: unknown) {
      return rejectWithValue(err instanceof Error ? err.message : 'Failed to fetch allowed fields');
    }
  }
);

export const createNewStyle = createAsyncThunk<CitationStyle, CreateCitationStyleRequest>(
  'styles/createNewStyle',
  async (data, { rejectWithValue }) => {
    try {
      return await createCitationStyle(data);
    } catch (err: unknown) {
      return rejectWithValue(err instanceof Error ? err.message : 'Failed to create citation style');
    }
  }
);

export const editStyle = createAsyncThunk<
  CitationStyle,
  { id: string; data: UpdateCitationStyleRequest }
>('styles/editStyle', async ({ id, data }, { rejectWithValue }) => {
  try {
    return await updateCitationStyle(id, data);
  } catch (err: unknown) {
    return rejectWithValue(err instanceof Error ? err.message : 'Failed to update citation style');
  }
});

export const removeStyle = createAsyncThunk<string, string>(
  'styles/removeStyle',
  async (id, { rejectWithValue }) => {
    try {
      await deleteCitationStyle(id);
      return id;
    } catch (err: unknown) {
      return rejectWithValue(err instanceof Error ? err.message : 'Failed to delete citation style');
    }
  }
);

export const stylesSlice = createSlice({
  name: 'styles',
  initialState,
  reducers: {
    setSelectedStyleId(state, action: PayloadAction<string | null>) {
      state.selectedStyleId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      // fetchStyles
      .addCase(fetchStyles.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchStyles.fulfilled, (state, action) => {
        state.isLoading = false;
        state.styles = action.payload;
        // Default to the first built-in style if not yet selected
        if (!state.selectedStyleId && action.payload.length > 0) {
          const defaultIop = action.payload.find((s) => s.slug === 'iop-default') || action.payload[0];
          state.selectedStyleId = defaultIop.id;
        }
      })
      .addCase(fetchStyles.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })

      // fetchAllowedFields
      .addCase(fetchAllowedFields.fulfilled, (state, action) => {
        state.allowedFields = action.payload;
      })

      // createNewStyle
      .addCase(createNewStyle.fulfilled, (state, action) => {
        state.styles.push(action.payload);
        state.selectedStyleId = action.payload.id;
      })

      // editStyle
      .addCase(editStyle.fulfilled, (state, action) => {
        const index = state.styles.findIndex((s) => s.id === action.payload.id);
        if (index !== -1) {
          state.styles[index] = action.payload;
        }
      })

      // removeStyle
      .addCase(removeStyle.fulfilled, (state, action) => {
        state.styles = state.styles.filter((s) => s.id !== action.payload);
        if (state.selectedStyleId === action.payload) {
          const fallback = state.styles.find((s) => s.is_builtin) || state.styles[0];
          state.selectedStyleId = fallback ? fallback.id : null;
        }
      });
  },
});

export const { setSelectedStyleId } = stylesSlice.actions;
export default stylesSlice.reducer;

