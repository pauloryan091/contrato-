// api.js - Cliente API para o CONTRATO+

const API_BASE_URL = `${window.location.origin}/api`;

class ContratoMaisAPI {
    constructor() {
        this.token = localStorage.getItem('token');
    }

    // ========== HEADERS ==========
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        return headers;
    }

    // ========== AUTENTICAÇÃO ==========
    async login(email, senha) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ email, senha }),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (data.success) {
                localStorage.setItem('user', JSON.stringify(data.user));
                localStorage.setItem('authenticated', 'true');
            }
            
            return data;
        } catch (error) {
            console.error('Erro no login:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async register(nome, email, senha) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ nome_completo: nome, email, senha }),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (data.success) {
                localStorage.setItem('user', JSON.stringify(data.user));
                localStorage.setItem('authenticated', 'true');
            }
            
            return data;
        } catch (error) {
            console.error('Erro no registro:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async logout() {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/logout`, {
                method: 'POST',
                headers: this.getHeaders(),
                credentials: 'include'
            });
            
            localStorage.removeItem('user');
            localStorage.removeItem('authenticated');
            localStorage.removeItem('token');
            
            return await response.json();
        } catch (error) {
            console.error('Erro no logout:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async checkAuth() {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/check`, {
                method: 'GET',
                headers: this.getHeaders(),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (data.authenticated) {
                localStorage.setItem('user', JSON.stringify(data.user));
                localStorage.setItem('authenticated', 'true');
            } else {
                localStorage.removeItem('user');
                localStorage.removeItem('authenticated');
            }
            
            return data;
        } catch (error) {
            console.error('Erro na verificação de autenticação:', error);
            return { authenticated: false };
        }
    }

    // ========== CONTRATOS ==========
    async getContratos() {
        try {
            const response = await fetch(`${API_BASE_URL}/contratos`, {
                method: 'GET',
                headers: this.getHeaders(),
                credentials: 'include'
            });
            
            if (response.status === 401) {
                return { success: false, authenticated: false };
            }
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar contratos:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async getContrato(id) {
        try {
            const response = await fetch(`${API_BASE_URL}/contratos/${id}`, {
                method: 'GET',
                headers: this.getHeaders(),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar contrato:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async criarContrato(contrato) {
        try {
            const response = await fetch(`${API_BASE_URL}/contratos`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(contrato),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao criar contrato:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async atualizarContrato(id, contrato) {
        try {
            const response = await fetch(`${API_BASE_URL}/contratos/${id}`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify(contrato),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao atualizar contrato:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async excluirContrato(id) {
        try {
            const response = await fetch(`${API_BASE_URL}/contratos/${id}`, {
                method: 'DELETE',
                headers: this.getHeaders(),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao excluir contrato:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    // ========== NOTIFICAÇÕES ==========
    async getNotificacoes() {
        try {
            const response = await fetch(`${API_BASE_URL}/notificacoes`, {
                method: 'GET',
                headers: this.getHeaders(),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar notificações:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async enviarNotificacao(contratoId, dados) {
        try {
            const response = await fetch(`${API_BASE_URL}/contratos/${contratoId}/notificar`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(dados),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao enviar notificação:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    // ========== DASHBOARD ==========
    async getDashboardStats() {
        try {
            const response = await fetch(`${API_BASE_URL}/dashboard/stats`, {
                method: 'GET',
                headers: this.getHeaders(),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar estatísticas:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    // ========== CONFIGURAÇÕES ==========
    async getPerfil() {
        try {
            const response = await fetch(`${API_BASE_URL}/configuracoes/perfil`, {
                method: 'GET',
                headers: this.getHeaders(),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao buscar perfil:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async atualizarPerfil(dados) {
        try {
            const response = await fetch(`${API_BASE_URL}/configuracoes/perfil`, {
                method: 'PUT',
                headers: this.getHeaders(),
                body: JSON.stringify(dados),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao atualizar perfil:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    // ========== UTILITÁRIOS ==========
    async testarEmail(email) {
        try {
            const response = await fetch(`${API_BASE_URL}/email/test`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ email }),
                credentials: 'include'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao testar email:', error);
            return { success: false, message: 'Erro de conexão com o servidor' };
        }
    }

    async verificarSistema() {
        try {
            const response = await fetch(`${API_BASE_URL}/system/health`, {
                method: 'GET',
                headers: this.getHeaders()
            });
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao verificar sistema:', error);
            return { status: 'error', message: 'Servidor indisponível' };
        }
    }

    // ========== HELPERS ==========
    formatarData(data) {
        if (!data) return '';
        const date = new Date(data);
        return date.toLocaleDateString('pt-BR') + ' ' + date.toLocaleTimeString('pt-BR');
    }

    formatarDataSimples(data) {
        if (!data) return '';
        const date = new Date(data);
        return date.toLocaleDateString('pt-BR');
    }

    calcularDiasRestantes(dataFim) {
        if (!dataFim) return 0;
        const hoje = new Date();
        const fim = new Date(dataFim);
        const diff = fim - hoje;
        return Math.ceil(diff / (1000 * 60 * 60 * 24));
    }

    getStatusBadge(status) {
        const statusConfig = {
            'ativo': { class: 'bg-green-100 text-green-800', label: 'Ativo' },
            'inativo': { class: 'bg-gray-100 text-gray-800', label: 'Inativo' },
            'pendente': { class: 'bg-yellow-100 text-yellow-800', label: 'Pendente' },
            'concluido': { class: 'bg-blue-100 text-blue-800', label: 'Concluído' },
            'vencido': { class: 'bg-red-100 text-red-800', label: 'Vencido' }
        };
        
        return statusConfig[status] || { class: 'bg-gray-100 text-gray-800', label: status };
    }

    getPrioridadeBadge(dias) {
        if (dias < 7) {
            return { class: 'bg-red-100 text-red-800', label: 'Urgente' };
        } else if (dias < 30) {
            return { class: 'bg-yellow-100 text-yellow-800', label: 'Atenção' };
        } else {
            return { class: 'bg-green-100 text-green-800', label: 'Normal' };
        }
    }

    // ========== VALIDAÇÕES ==========
    validarEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    }

    validarSenha(senha) {
        return senha.length >= 6;
    }

    // ========== GESTÃO DE ERROS ==========
    handleApiError(error, defaultMessage = 'Erro na operação') {
        console.error('API Error:', error);
        
        if (error.response) {
            // Erro da API
            return {
                success: false,
                message: error.response.data?.message || defaultMessage,
                status: error.response.status
            };
        } else if (error.request) {
            // Erro de rede
            return {
                success: false,
                message: 'Erro de conexão com o servidor',
                status: 0
            };
        } else {
            // Erro na configuração da requisição
            return {
                success: false,
                message: defaultMessage,
                status: -1
            };
        }
    }

    // ========== GESTÃO DE SESSÃO ==========
    isAuthenticated() {
        return localStorage.getItem('authenticated') === 'true';
    }

    getUser() {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    }

    clearSession() {
        localStorage.removeItem('user');
        localStorage.removeItem('authenticated');
        localStorage.removeItem('token');
    }

    // ========== INTERCEPTOR DE REQUISIÇÕES ==========
    setupInterceptor() {
        // Interceptar todas as requisições fetch
        const originalFetch = window.fetch;
        
        window.fetch = async (...args) => {
            try {
                const response = await originalFetch(...args);
                
                // Verificar se é uma resposta não autorizada
                if (response.status === 401 && !args[0].includes('/auth/')) {
                    // Limpar sessão local
                    this.clearSession();
                    
                    // Redirecionar para login
                    window.location.href = '/';
                    
                    return response;
                }
                
                return response;
            } catch (error) {
                console.error('Fetch interceptor error:', error);
                throw error;
            }
        };
    }
}

// Criar instância global da API
const api = new ContratoMaisAPI();

// Inicializar interceptor
api.setupInterceptor();

// Funções auxiliares globais
window.showLoading = function() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'flex';
};

window.hideLoading = function() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'none';
};

window.showToast = function(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 24px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
};

// Adicionar estilos para animações
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255, 255, 255, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        backdrop-filter: blur(4px);
    }
    
    .loading-spinner {
        width: 50px;
        height: 50px;
        border: 4px solid #e5e7eb;
        border-top-color: #3b82f6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
`;

document.head.appendChild(style);

// Adicionar elemento de loading global
const loadingOverlay = document.createElement('div');
loadingOverlay.id = 'loading';
loadingOverlay.className = 'loading-overlay';
loadingOverlay.style.display = 'none';
loadingOverlay.innerHTML = '<div class="loading-spinner"></div>';
document.body.appendChild(loadingOverlay);

// Exportar API globalmente
window.ContratoMaisAPI = api;