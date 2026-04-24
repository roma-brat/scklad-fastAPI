/**
 * Tailwind CSS Configuration
 * Windows 11 Fluent — светлая тема
 */

tailwind.config = {
    darkMode: 'class',  // НЕ используем media prefers-color-scheme
    theme: {
        extend: {
            colors: {
                // Windows 11 Fluent — светлая тема (белый фон)
                page: '#ffffff',
                surface: '#ffffff',
                'surface-hover': '#f5f5f5',
                elevated: '#ffffff',
                border: {
                    primary: '#e5e7eb',
                    secondary: '#d1d5db',
                },
                text: {
                    primary: '#1a1a1a',
                    secondary: '#616161',
                    tertiary: '#9e9e9e',
                },
                accent: {
                    DEFAULT: '#0067c0',
                    hover: '#005a9e',
                    bg: '#e8f4ff',
                },
                success: {
                    DEFAULT: '#0f7b0f',
                    bg: '#f1faf1',
                    border: '#d2e8d2',
                },
                error: {
                    DEFAULT: '#c42b1c',
                    bg: '#fdf3f2',
                    border: '#f4b4a9',
                },
                warning: {
                    DEFAULT: '#9d5d00',
                    bg: '#fef9f0',
                    border: '#fce6b3',
                },
                info: {
                    DEFAULT: '#0078d4',
                    bg: '#f0f6ff',
                    border: '#b3d9ff',
                },
            },
            fontFamily: {
                sans: ['"Segoe UI"', '-apple-system', 'BlinkMacSystemFont', 'Roboto', 'sans-serif'],
            },
            boxShadow: {
                card: '0 2px 4px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06)',
                'card-hover': '0 8px 16px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
                elevated: '0 32px 64px rgba(0, 0, 0, 0.12), 0 8px 16px rgba(0, 0, 0, 0.08)',
                modal: '0 24px 48px rgba(0, 0, 0, 0.12)',
            },
            borderRadius: {
                'win-sm': '4px',
                'win-md': '8px',
                'win-lg': '12px',
                'win-xl': '16px',
            },
        }
    }
};
