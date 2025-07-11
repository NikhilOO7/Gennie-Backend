export const styles = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
    padding: '24px'
  },
  button: {
    backgroundColor: '#4f46e5',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s'
  },
  input: {
    width: '100%',
    padding: '12px',
    border: '2px solid #e5e7eb',
    borderRadius: '8px',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s'
  },
  sidebar: {
    width: '320px',
    backgroundColor: 'white',
    borderRight: '1px solid #e5e7eb',
    display: 'flex',
    flexDirection: 'column',
    height: '100vh'
  },
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100vh'
  },
  message: {
    maxWidth: '70%',
    padding: '12px 16px',
    borderRadius: '12px',
    marginBottom: '8px',
    wordWrap: 'break-word'
  },
  userMessage: {
    backgroundColor: '#4f46e5',
    color: 'white',
    marginLeft: 'auto'
  },
  aiMessage: {
    backgroundColor: '#f3f4f6',
    color: '#374151',
    marginRight: 'auto'
  }
};

export const darkModeStyles = {
  container: {
    backgroundColor: '#1f2937'
  },
  sidebar: {
    backgroundColor: '#111827',
    borderColor: '#374151'
  },
  card: {
    backgroundColor: '#374151',
    color: '#f3f4f6'
  },
  input: {
    backgroundColor: '#4b5563',
    borderColor: '#6b7280',
    color: '#f3f4f6'
  }
};

export const getThemeStyles = (darkMode) => {
  if (!darkMode) return styles;
  
  return {
    ...styles,
    container: { ...styles.container, ...darkModeStyles.container },
    sidebar: { ...styles.sidebar, ...darkModeStyles.sidebar },
    card: { ...styles.card, ...darkModeStyles.card },
    input: { ...styles.input, ...darkModeStyles.input }
  };
};