import React from 'react';
import { Activity, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { styles } from '../../utils/styles';
import { getStatusColor, getErrorMessage } from '../../utils/helpers';

const HealthDashboard = ({ healthStatus, onRefresh }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle size={20} color="#10b981" />;
      case 'degraded':
        return <AlertCircle size={20} color="#f59e0b" />;
      case 'unhealthy':
        return <AlertCircle size={20} color="#ef4444" />;
      default:
        return <Clock size={20} color="#6b7280" />;
    }
  };

  return (
    <div style={{ padding: '24px', backgroundColor: '#f9fafb', height: '100%', overflowY: 'auto' }}>
      <div style={{ ...styles.card, marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: '600' }}>System Health</h2>
          <button onClick={onRefresh} style={styles.button}>
            Refresh
          </button>
        </div>

        {healthStatus ? (
          <div>
            {/* Overall Status */}
            <div style={{ marginBottom: '32px' }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px',
                padding: '16px',
                backgroundColor: '#f3f4f6',
                borderRadius: '8px',
                marginBottom: '16px'
              }}>
                <div>
                  {getStatusIcon(healthStatus.status)}
                </div>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Overall Status</h3>
                  <p style={{ 
                    color: getStatusColor(healthStatus.status), 
                    textTransform: 'capitalize',
                    fontWeight: '500'
                  }}>
                    {healthStatus.status}
                  </p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
                    {healthStatus.version}
                  </p>
                  <p style={{ fontSize: '12px', color: '#6b7280' }}>Version</p>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
                    {healthStatus.environment}
                  </p>
                  <p style={{ fontSize: '12px', color: '#6b7280' }}>Environment</p>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '24px', fontWeight: '600', color: '#4f46e5' }}>
                    {Math.round(healthStatus.response_time_seconds * 1000)}ms
                  </p>
                  <p style={{ fontSize: '12px', color: '#6b7280' }}>Response Time</p>
                </div>
              </div>
            </div>

            {/* Service Checks */}
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
                Service Status
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {Object.entries(healthStatus.checks).map(([service, check]) => (
                  <div
                    key={service}
                    style={{
                      padding: '16px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '8px',
                      border: '1px solid #e5e7eb'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h4 style={{ fontSize: '14px', fontWeight: '500', textTransform: 'capitalize' }}>
                        {service.replace('_', ' ')}
                      </h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {getStatusIcon(check.status)}
                        <span style={{ color: getStatusColor(check.status), fontWeight: '500' }}>
                          {check.status}
                        </span>
                      </div>
                    </div>
                    {check.response_time_ms && (
                      <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                        Response time: {Math.round(check.response_time_ms)}ms
                      </p>
                    )}
                    {check.error && (
                      <p style={{ fontSize: '12px', color: '#ef4444', marginTop: '4px' }}>
                        Error: {getErrorMessage(check.error)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Activity size={48} color="#e5e7eb" />
            <h3 style={{ marginTop: '16px', color: '#6b7280' }}>
              Loading Health Status
            </h3>
            <p style={{ marginTop: '8px', color: '#9ca3af' }}>
              Fetching system health information...
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default HealthDashboard;