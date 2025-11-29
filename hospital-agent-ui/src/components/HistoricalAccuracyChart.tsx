import { Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Line, ComposedChart } from 'recharts';

interface HistoricalData {
    date: string;
    predicted: number;
    actual: number;
    accuracy: number;
}

interface HistoricalAccuracyChartProps {
    data: HistoricalData[];
}

export default function HistoricalAccuracyChart({ data }: HistoricalAccuracyChartProps) {
    // Format data for chart
    const chartData = data.map((item) => ({
        date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        predicted: item.predicted,
        actual: item.actual,
        accuracy: item.accuracy,
        variance: Math.abs(item.predicted - item.actual),
    }));

    // Custom tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div style={{
                    background: 'white',
                    border: '1px solid #E5E7EB',
                    borderRadius: '8px',
                    padding: '12px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}>
                    <p style={{ fontWeight: 600, marginBottom: '8px', color: '#111827' }}>
                        {data.date}
                    </p>
                    <p style={{ color: '#3B82F6', fontSize: '14px', marginBottom: '4px' }}>
                        Predicted: <strong>{data.predicted}</strong>
                    </p>
                    <p style={{ color: '#10B981', fontSize: '14px', marginBottom: '4px' }}>
                        Actual: <strong>{data.actual}</strong>
                    </p>
                    <p style={{ color: '#F59E0B', fontSize: '14px', marginBottom: '4px' }}>
                        Variance: <strong>{data.variance}</strong>
                    </p>
                    <p style={{
                        color: data.accuracy >= 95 ? '#10B981' : data.accuracy >= 90 ? '#F59E0B' : '#EF4444',
                        fontSize: '13px',
                        fontWeight: 600,
                        marginTop: '8px',
                        paddingTop: '8px',
                        borderTop: '1px solid #E5E7EB'
                    }}>
                        Accuracy: {data.accuracy.toFixed(1)}%
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div style={{ width: '100%', height: '350px' }}>
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis
                        dataKey="date"
                        stroke="#6B7280"
                        style={{ fontSize: '12px' }}
                    />
                    <YAxis
                        yAxisId="left"
                        stroke="#6B7280"
                        style={{ fontSize: '12px' }}
                        label={{ value: 'Admissions', angle: -90, position: 'insideLeft', style: { fontSize: '12px', fill: '#6B7280' } }}
                    />
                    <YAxis
                        yAxisId="right"
                        orientation="right"
                        stroke="#F59E0B"
                        style={{ fontSize: '12px' }}
                        label={{ value: 'Accuracy %', angle: 90, position: 'insideRight', style: { fontSize: '12px', fill: '#6B7280' } }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{ fontSize: '14px', paddingTop: '20px' }}
                    />
                    <Bar
                        yAxisId="left"
                        dataKey="predicted"
                        fill="#3B82F6"
                        name="Predicted"
                        radius={[4, 4, 0, 0]}
                    />
                    <Bar
                        yAxisId="left"
                        dataKey="actual"
                        fill="#10B981"
                        name="Actual"
                        radius={[4, 4, 0, 0]}
                    />
                    <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="accuracy"
                        stroke="#F59E0B"
                        strokeWidth={2}
                        dot={{ fill: '#F59E0B', r: 4 }}
                        name="Accuracy %"
                    />
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    );
}