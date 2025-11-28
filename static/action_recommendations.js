// Funcție JavaScript pentru generarea recomandărilor de acțiune
async function generateActionRecommendations(agentId, focusAreas = null) {
    try {
        const url = `/agents/${agentId}/action-recommendations`;
        const options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                focus_areas: focusAreas || ['seo', 'social_media', 'content', 'ux', 'technical']
            })
        };
        
        const response = await fetch(url, options);
        const data = await response.json();
        
        if (data.ok) {
            displayActionRecommendations(data);
        } else {
            showError('Eroare la generarea recomandărilor: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Eroare la conectarea la server');
    }
}

function displayActionRecommendations(data) {
    const container = document.getElementById('action-recommendations-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="action-recommendations-header">
            <h2>🎯 Plan de Acțiune - Recomandări Practice</h2>
            <p>Bazat pe analiza a ${data.competitors_analyzed || 0} competitori</p>
        </div>
        
        <div class="quick-wins-section">
            <h3>⚡ Quick Wins (Implementare Rapidă)</h3>
            <div class="quick-wins-grid">
                ${(data.action_plan?.quick_wins || []).map(win => `
                    <div class="recommendation-card quick-win">
                        <div class="rec-header">
                            <span class="impact-badge impact-${win.impact?.toLowerCase()}">${win.impact}</span>
                            <span class="time-badge">${win.estimated_time || 'N/A'}</span>
                        </div>
                        <h4>${win.title}</h4>
                        <p>${win.description}</p>
                        <div class="rec-steps">
                            <strong>Pași:</strong>
                            <ol>
                                ${(win.steps || []).map(step => `<li>${step}</li>`).join('')}
                            </ol>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div class="recommendations-by-area">
            ${Object.entries(data.recommendations || {}).map(([area, areaData]) => `
                <div class="area-section">
                    <h3>${getAreaIcon(area)} ${areaData.area || area.toUpperCase()}</h3>
                    <div class="recommendations-grid">
                        ${(areaData.recommendations || []).map(rec => `
                            <div class="recommendation-card">
                                <div class="rec-header">
                                    <span class="impact-badge impact-${rec.impact?.toLowerCase()}">${rec.impact}</span>
                                    <span class="time-badge">${rec.estimated_time || 'N/A'}</span>
                                </div>
                                <h4>${rec.title}</h4>
                                <p>${rec.description}</p>
                                ${rec.category ? `<span class="category-badge">${rec.category}</span>` : ''}
                                ${rec.platform ? `<span class="platform-badge">${rec.platform}</span>` : ''}
                                <div class="rec-steps">
                                    <strong>Pași de implementare:</strong>
                                    <ol>
                                        ${(rec.steps || []).map(step => `<li>${step}</li>`).join('')}
                                    </ol>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="action-plan-section">
            <h3>📅 Plan de Acțiune - 30 de Zile</h3>
            <div class="week-plans">
                ${['week_1', 'week_2', 'week_3', 'week_4'].map((week, idx) => {
                    const weekPlan = data.action_plan && data.action_plan['30_day_plan'] ? data.action_plan['30_day_plan'][week] : [];
                    return `
                    <div class="week-plan">
                        <h4>Săptămâna ${idx + 1}</h4>
                        <ul>
                            ${(weekPlan || []).map(rec => `
                                <li>
                                    <strong>${rec.title}</strong>
                                    <span class="impact-small impact-${rec.impact?.toLowerCase()}">${rec.impact}</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                `;
                }).join('')}
            </div>
        </div>
    `;
}

function getAreaIcon(area) {
    const icons = {
        'seo': '🔍',
        'social_media': '📱',
        'content': '📝',
        'ux': '🎨',
        'technical': '⚙️'
    };
    return icons[area] || '📌';
}

function showError(message) {
    const container = document.getElementById('action-recommendations-container');
    if (container) {
        container.innerHTML = `
            <div class="error-message">
                <span style="color: red;">❌ ${message}</span>
            </div>
        `;
    }
}

// CSS pentru recomandări
const actionRecommendationsCSS = `
<style>
.action-recommendations-container {
    background: white;
    border-radius: 12px;
    padding: 30px;
    margin: 20px 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.action-recommendations-header {
    text-align: center;
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 2px solid #667eea;
}

.action-recommendations-header h2 {
    color: #667eea;
    margin-bottom: 10px;
}

.quick-wins-section {
    margin-bottom: 40px;
}

.quick-wins-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-top: 20px;
}

.recommendation-card {
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    transition: transform 0.2s, box-shadow 0.2s;
}

.recommendation-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.recommendation-card.quick-win {
    border-left: 4px solid #28a745;
    background: #f0fff4;
}

.rec-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.impact-badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: bold;
    text-transform: uppercase;
}

.impact-high {
    background: #ff6b6b;
    color: white;
}

.impact-medium {
    background: #ffd93d;
    color: #333;
}

.impact-low {
    background: #6bcf7f;
    color: white;
}

.time-badge {
    background: #667eea;
    color: white;
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 0.8rem;
}

.recommendation-card h4 {
    color: #333;
    margin-bottom: 10px;
    font-size: 1.1rem;
}

.recommendation-card p {
    color: #666;
    margin-bottom: 15px;
    line-height: 1.6;
}

.category-badge, .platform-badge {
    display: inline-block;
    background: #e0e0e0;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    margin-right: 5px;
    margin-bottom: 10px;
}

.rec-steps {
    margin-top: 15px;
    padding-top: 15px;
    border-top: 1px solid #e0e0e0;
}

.rec-steps strong {
    display: block;
    margin-bottom: 10px;
    color: #333;
}

.rec-steps ol {
    margin-left: 20px;
    color: #555;
}

.rec-steps li {
    margin-bottom: 8px;
    line-height: 1.5;
}

.area-section {
    margin-bottom: 40px;
}

.area-section h3 {
    color: #667eea;
    margin-bottom: 20px;
    font-size: 1.5rem;
    padding-bottom: 10px;
    border-bottom: 2px solid #e0e0e0;
}

.recommendations-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 20px;
}

.action-plan-section {
    margin-top: 40px;
    padding-top: 30px;
    border-top: 2px solid #667eea;
}

.action-plan-section h3 {
    color: #667eea;
    margin-bottom: 20px;
}

.week-plans {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
}

.week-plan {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}

.week-plan h4 {
    color: #667eea;
    margin-bottom: 15px;
}

.week-plan ul {
    list-style: none;
    padding: 0;
}

.week-plan li {
    padding: 8px 0;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.impact-small {
    padding: 2px 8px;
    border-radius: 8px;
    font-size: 0.7rem;
    font-weight: bold;
}

.error-message {
    padding: 20px;
    text-align: center;
    background: #fff3cd;
    border: 1px solid #ffc107;
    border-radius: 8px;
}

.btn-generate-recommendations {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    margin: 10px 0;
}

.btn-generate-recommendations:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-generate-recommendations:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
</style>
`;

