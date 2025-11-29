import { Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';

interface Prediction {
    date: string;
    predicted_admissions: number;
    confidence: number;
    risk_level: string;
}

interface AdmissionForecastChartProps {
    predictions: Prediction[];
}

export default function AdmissionForecastChart({ predictions }: AdmissionForecastChartProps) {
    // Format data for chart
    const chartData = predictions.map((pred) => ({
        date: new Date(pred.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        admissions: pred.predicted_admissions,
        confidence: pred.confidence * 100,
        upperBound: pred.predicted_admissions * (1 + (1 - pred.confidence) * 0.5),
        lowerBound: pred.predicted_admissions * (1 - (1 - pred.confidence) * 0.5),
    }));

    // Custom tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            return (
                <div style={{
                    background: 'white',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    padding: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}>
                    <p style={{ fontWeight: 600, marginBottom: '8px', color: '#111827' }}>
                        {payload[0].payload.date}
                    </p>
                    <p style={{ color: '#3B82F6', fontSize: '14px' }}>
                        Admissions: <strong>{Math.round(payload[0].value)}</strong>
                    </p>
                    <p style={{ color: '#6B7280', fontSize: '13px' }}>
                        Confidence: {Math.round(payload[0].payload.confidence)}%
                    </p>
                    <p style={{ color: '#9CA3AF', fontSize: '12px', marginTop: '4px' }}>
                        Range: {Math.round(payload[0].payload.lowerBound)} - {Math.round(payload[0].payload.upperBound)}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div style={{ width: '100%', height: '350px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorAdmissions" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis
                        dataKey="date"
                        stroke="#6B7280"
                        style={{ fontSize: '12px' }}
                    />
                    <YAxis
                        stroke="#6B7280"
                        style={{ fontSize: '12px' }}
                        label={{ value: 'Admissions', angle: -90, position: 'insideLeft', style: { fontSize: '12px', fill: '#6B7280' } }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{ fontSize: '14px', paddingTop: '20px' }}
                        iconType="line"
                    />
                    <Area
                        type="monotone"
                        dataKey="upperBound"
                        stroke="none"
                        fill="#DBEAFE"
                        fillOpacity={0.3}
                    />
                    <Area
                        type="monotone"
                        dataKey="lowerBound"
                        stroke="none"
                        fill="#DBEAFE"
                        fillOpacity={0.3}
                    />
                    <Line
                        type="monotone"
                        dataKey="admissions"
                        stroke="#3B82F6"
                        strokeWidth={3}
                        dot={{ fill: '#3B82F6', r: 4 }}
                        activeDot={{ r: 6 }}
                        name="Predicted Admissions"
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}