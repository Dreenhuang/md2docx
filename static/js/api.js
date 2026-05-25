/**
 * md2docx - API 对接层
 * 封装所有后端 REST API 调用，使用原生 Fetch API
 * 前端通过此模块与后端通信，实现关注点分离
 */

const API_BASE = '/api';

const Api = {
    /* ============================================
       文件操作相关 API
       ============================================ */

    /**
     * 浏览选择输入路径（文件夹）
     * @param {string} path - 文件夹路径
     * @returns {Promise<Object>} {success, files[], message}
     */
    browseInput: function(path) {
        return fetch(API_BASE + '/browse/input', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 浏览选择输出路径（文件夹）
     * @param {string} path - 输出文件夹路径
     * @returns {Promise<Object>} {success, path, message}
     */
    browseOutput: function(path) {
        return fetch(API_BASE + '/browse/output', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 获取当前文件列表
     * @returns {Promise<Object>} {success, files[]}
     * files: [{id, name, path, status}]
     */
    getFiles: function() {
        return fetch(API_BASE + '/files', {
            method: 'GET'
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 添加文件到转换列表
     * @param {Object[]} fileList - 文件对象数组 [{name, path, size}]
     * @returns {Promise<Object>} {success, addedCount, files[]}
     */
    addFiles: function(fileList) {
        return fetch(API_BASE + '/files', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: fileList })
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 从列表中移除单个文件
     * @param {string|number} fileId - 文件 ID
     * @returns {Promise<Object>} {success, message}
     */
    removeFile: function(fileId) {
        return fetch(API_BASE + '/files/' + fileId, {
            method: 'DELETE'
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 清空整个文件列表
     * @returns {Promise<Object>} {success, message}
     */
    clearFiles: function() {
        return fetch(API_BASE + '/files', {
            method: 'DELETE'
        }).then(function(resp) { return resp.json(); });
    },

    /* ============================================
       转换控制相关 API
       ============================================ */

    /**
     * 开始批量转换任务
     * @param {Object} config - 转换配置参数
     * @param {string} config.inputPath - 输入路径
     * @param {string} config.outputPath - 输出路径
     * @param {boolean} config.sameDir - 是否输出到同目录
     * @param {Object} config.format - 格式配置
     * @returns {Promise<Object>} {success, taskId, totalFiles}
     */
    startConversion: function(config) {
        return fetch(API_BASE + '/convert/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 停止当前正在执行的转换任务
     * @returns {Promise<Object>} {success, completedCount, message}
     */
    stopConversion: function() {
        return fetch(API_BASE + '/convert/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 获取当前转换进度
     * @returns {Promise<Object>}
     * {status, progress, currentFile, currentIndex, totalCount,
     *  completedFiles[], failedFiles[], logs[]}
     */
    getProgress: function() {
        return fetch(API_BASE + '/convert/progress', {
            method: 'GET'
        }).then(function(resp) { return resp.json(); });
    },

    /* ============================================
       配置管理相关 API
       ============================================ */

    /**
     * 获取当前格式配置
     * @returns {Promise<Object>} 格式配置对象
     */
    getConfig: function() {
        return fetch(API_BASE + '/config', {
            method: 'GET'
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 更新格式配置
     * @param {Object} config - 配置参数
     * @returns {Promise<Object>} {success, config, message}
     */
    updateConfig: function(config) {
        return fetch(API_BASE + '/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 恢复默认配置
     * @returns {Promise<Object>} {success, defaultConfig, message}
     */
    resetConfig: function() {
        return fetch(API_BASE + '/config/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        }).then(function(resp) { return resp.json(); });
    },

    /* ============================================
       日志系统相关 API
       ============================================ */

    /**
     * 获取转换日志列表
     * @param {number} limit - 返回日志条数上限，默认 100
     * @returns {Promise<Object>} {success, logs[]}
     * logs: [{timestamp, level, message}]
     */
    getLogs: function(limit) {
        var url = API_BASE + '/logs';
        if (limit) url += '?limit=' + limit;
        return fetch(url, {
            method: 'GET'
        }).then(function(resp) { return resp.json(); });
    },

    /**
     * 导出日志为文本文件
     * @param {string} format - 导出格式：txt | json
     * @returns {Promise<Blob>} 日志文件 Blob 对象
     */
    exportLogs: function(format) {
        format = format || 'txt';
        return fetch(API_BASE + '/logs/export?format=' + format, {
            method: 'GET'
        }).then(function(resp) { return resp.blob(); });
    },

    /* ============================================
       工具方法
       ============================================ */

    /**
     * 通用请求错误处理
     * @param {Error} error - 错误对象
     * @param {string} operation - 操作名称（用于日志）
     * @returns {Object} 标准化错误响应
     */
    handleError: function(error, operation) {
        console.error('[API Error] ' + operation + ':', error);
        return {
            success: false,
            error: error.message || '网络请求失败',
            operation: operation
        };
    },

    /**
     * 检查 API 服务是否可用
     * @returns {Promise<boolean>} 是否可用
     */
    healthCheck: function() {
        return fetch(API_BASE + '/health', {
            method: 'GET'
        }).then(function(resp) { return resp.ok; })
          .catch(function() { return false; });
    }
};
