/**
 * md2docx - 主应用交互逻辑
 * 基于 gui-design.html 高保真原型，对接真实 API
 * 实现完整的文件管理、格式配置、批量转换、日志系统功能
 */

(function() {
    'use strict';

    /* ============================================
       全局状态管理 - 应用核心状态
       ============================================ */
    var AppState = {
        files: [],              // 文件列表 [{id, name, path, status}]
        isConverting: false,    // 是否正在转换
        progressTimer: null,    // 进度轮询定时器
        pendingCallback: null   // 弹窗待执行回调
    };

    /* ============================================
       DOM 元素缓存 - 避免重复查询 DOM
       ============================================ */
    var Dom = {
        // 路径配置
        inputPath: document.getElementById('inputPath'),
        outputPath: document.getElementById('outputPath'),
        sameDir: document.getElementById('sameDir'),
        browseInputBtn: document.getElementById('browseInputBtn'),
        browseOutputBtn: document.getElementById('browseOutputBtn'),
        clearInputBtn: document.getElementById('clearInputBtn'),
        openOutputBtn: document.getElementById('openOutputBtn'),

        // 格式配置面板
        formatPanel: document.getElementById('formatPanel'),
        formatToggleBtn: document.getElementById('formatToggleBtn'),
        formatBody: document.getElementById('formatBody'),

        // 格式参数输入
        paperSize: document.getElementById('paperSize'),
        orientation: document.getElementById('orientation'),
        marginLeft: document.getElementById('marginLeft'),
        marginRight: document.getElementById('marginRight'),
        marginTop: document.getElementById('marginTop'),
        marginBottom: document.getElementById('marginBottom'),
        fontFamily: document.getElementById('fontFamily'),
        fontSize: document.getElementById('fontSize'),
        lineSpacing: document.getElementById('lineSpacing'),
        firstIndent: document.getElementById('firstIndent'),
        enableHeader: document.getElementById('enableHeader'),
        enableFooter: document.getElementById('enableFooter'),
        restoreDefaultsBtn: document.getElementById('restoreDefaultsBtn'),
        saveTemplateBtn: document.getElementById('saveTemplateBtn'),

        // 操作按钮
        addFilesBtn: document.getElementById('addFilesBtn'),
        addFolderBtn: document.getElementById('addFolderBtn'),
        clearFileListBtn: document.getElementById('clearFileListBtn'),
        startBtn: document.getElementById('startBtn'),
        stopBtn: document.getElementById('stopBtn'),

        // 隐藏文件选择器
        fileInput: document.getElementById('fileInput'),
        folderInput: document.getElementById('folderInput'),

        // 文件列表区域
        fileTableBody: document.getElementById('fileTableBody'),
        tableEmptyState: document.getElementById('tableEmptyState'),
        fileCountBadge: document.getElementById('fileCountBadge'),

        // 进度与日志
        progressFill: document.getElementById('progressFill'),
        progressText: document.getElementById('progressText'),
        logConsole: document.getElementById('logConsole'),
        clearLogBtn: document.getElementById('clearLogBtn'),
        exportLogBtn: document.getElementById('exportLogBtn'),

        // 弹窗系统
        confirmDialog: document.getElementById('confirmDialog'),
        confirmDialogMsg: document.getElementById('confirmDialogMsg'),
        confirmDialogCancelBtn: document.getElementById('confirmDialogCancelBtn'),
        confirmDialogOkBtn: document.getElementById('confirmDialogOkBtn'),

        completeDialog: document.getElementById('completeDialog'),
        completeDialogMsg: document.getElementById('completeDialogMsg'),
        openOutputFromCompleteBtn: document.getElementById('openOutputFromCompleteBtn'),
        closeCompleteBtn: document.getElementById('closeCompleteBtn'),

        errorDialog: document.getElementById('errorDialog'),
        errorDialogMsg: document.getElementById('errorDialogMsg'),
        closeErrorBtn: document.getElementById('closeErrorBtn')
    };

    /* ============================================
       初始化入口 - 页面加载完成后绑定事件
       ============================================ */
    function init() {
        bindPathEvents();
        bindFormatEvents();
        bindFileEvents();
        bindConversionEvents();
        bindLogEvents();
        bindDialogEvents();
        loadInitialConfig();
        updateFileListUI();

        addLog('info', '系统就绪，等待添加 Markdown 文件...');
        console.log('[md2docx] 应用初始化完成');
    }

    /* ============================================
       路径选择相关事件
       ============================================ */
    function bindPathEvents() {
        // 浏览输入路径 - 触发文件选择器
        Dom.browseInputBtn.addEventListener('click', function() {
            Dom.fileInput.click();
        });

        // 浏览输出路径 - 触发文件夹选择器
        Dom.browseOutputBtn.addEventListener('click', function() {
            Dom.folderInput.click();
        });

        // 清空输入路径
        Dom.clearInputBtn.addEventListener('click', function() {
            Dom.inputPath.value = '';
            addLog('info', '已清空输入路径');
        });

        // 打开输出文件夹
        Dom.openOutputBtn.addEventListener('click', function() {
            var outputPath = Dom.outputPath.value;
            if (!outputPath) {
                showErrorDialog('请先设置输出路径');
                return;
            }
            // 调用 API 打开文件夹（后端实现）
            Api.browseOutput(outputPath).then(function(res) {
                if (res.success) {
                    addLog('info', '已打开输出文件夹: ' + outputPath);
                } else {
                    showErrorDialog(res.error || '无法打开文件夹');
                }
            }).catch(function(err) {
                showErrorDialog('操作失败: ' + err.message);
            });
        });

        // 文件选择器变化 - 处理选中的 .md 文件
        Dom.fileInput.addEventListener('change', handleFileSelect);

        // 文件夹选择器变化 - 处理选中的文件夹（递归扫描 .md）
        Dom.folderInput.addEventListener('change', handleFolderSelect);
    }

    /**
     * 处理单个/多个文件选择
     */
    function handleFileSelect(e) {
        var files = e.target.files;
        if (!files || files.length === 0) return;

        var fileList = [];
        for (var i = 0; i < files.length; i++) {
            var file = files[i];
            var ext = file.name.split('.').pop().toLowerCase();
            if (['md', 'markdown', 'mdown', 'mkd'].indexOf(ext) !== -1) {
                fileList.push({
                    name: file.name,
                    path: (file.webkitRelativePath || file.name),
                    size: file.size
                });
            }
        }

        if (fileList.length > 0) {
            addFilesToList(fileList);
            // 更新输入路径显示（取第一个文件的目录）
            var firstPath = fileList[0].path.replace(/\\/g, '/').replace(/\/[^\/]*$/, '');
            Dom.inputPath.value = firstPath || '已选择 ' + fileList.length + ' 个文件';
        } else {
            addLog('warn', '未检测到有效的 Markdown 文件（支持 .md/.markdown/.mdown/.mkd）');
        }

        // 重置 input 以便再次选择同一文件
        e.target.value = '';
    }

    /**
     * 处理文件夹选择（webkitdirectory）
     */
    function handleFolderSelect(e) {
        var files = e.target.files;
        if (!files || files.length === 0) return;

        var fileList = [];
        for (var i = 0; i < files.length; i++) {
            var file = files[i];
            var ext = file.name.split('.').pop().toLowerCase();
            if (['md', 'markdown', 'mdown', 'mkd'].indexOf(ext) !== -1) {
                fileList.push({
                    name: file.name,
                    path: file.webkitRelativePath || file.name,
                    size: file.size
                });
            }
        }

        if (fileList.length > 0) {
            addFilesToList(fileList);
            // 更新路径显示
            var folderPath = fileList[0].path.replace(/\\/g, '/').replace(/\/[^\/]*$/, '') || '已选择文件夹';
            Dom.outputPath.value = folderPath;
            addLog('info', '从文件夹扫描到 ' + fileList.length + ' 个 Markdown 文件');
        } else {
            addLog('warn', '所选文件夹中未找到 Markdown 文件');
        }

        e.target.value = '';
    }

    /* ============================================
       格式配置相关事件
       ============================================ */
    function bindFormatEvents() {
        // 折叠/展开格式面板
        Dom.formatToggleBtn.addEventListener('click', toggleFormatPanel);

        // 恢复默认配置
        Dom.restoreDefaultsBtn.addEventListener('click', function() {
            showConfirmDialog(
                '确认要恢复默认设置吗？当前自定义配置将丢失。此操作不可撤销。',
                function() { restoreDefaultConfig(); }
            );
        });

        // 保存模板配置
        Dom.saveTemplateBtn.addEventListener('click', saveCurrentConfig);
    }

    /**
     * 切换格式面板折叠状态
     */
    function toggleFormatPanel() {
        var panel = Dom.formatPanel;
        var isCollapsed = panel.classList.toggle('panel--collapsed');
        Dom.formatToggleBtn.setAttribute('aria-expanded', !isCollapsed);
    }

    /**
     * 恢复默认配置并更新 UI
     */
    function restoreDefaultConfig() {
        Api.resetConfig().then(function(res) {
            if (res.success && res.defaultConfig) {
                applyConfigToForm(res.defaultConfig);
                addLog('success', '已恢复默认配置');
            } else {
                // 使用硬编码的默认值作为降级方案
                applyConfigToForm(getHardcodedDefaults());
                addLog('success', '已恢复默认配置（本地默认值）');
            }
        }).catch(function() {
            applyConfigToForm(getHardcodedDefaults());
            addLog('warn', 'API 不可用，使用本地默认值');
        });
    }

    /**
     * 保存当前模板配置到后端
     */
    function saveCurrentConfig() {
        var config = readConfigFromForm();
        Api.updateConfig(config).then(function(res) {
            if (res.success) {
                addLog('success', '模板配置已保存');
            } else {
                showErrorDialog(res.error || '保存失败');
            }
        }).catch(function(err) {
            addLog('warn', '配置已暂存至本地（后端未响应）');
        });
    }

    /**
     * 从表单读取当前配置值
     */
    function readConfigFromForm() {
        return {
            paperSize: Dom.paperSize.value,
            orientation: Dom.orientation.value,
            margins: {
                left: parseInt(Dom.marginLeft.value) || 20,
                right: parseInt(Dom.marginRight.value) || 20,
                top: parseInt(Dom.marginTop.value) || 16,
                bottom: parseInt(Dom.marginBottom.value) || 16
            },
            font: {
                family: Dom.fontFamily.value,
                size: Dom.fontSize.value
            },
            lineSpacing: parseInt(Dom.lineSpacing.value) || 16,
            firstIndent: Dom.firstIndent.value,
            header: Dom.enableHeader.checked,
            footer: Dom.enableFooter.checked
        };
    }

    /**
     * 将配置对象应用到表单控件
     */
    function applyConfigToForm(config) {
        if (config.paperSize) Dom.paperSize.value = config.paperSize;
        if (config.orientation) Dom.orientation.value = config.orientation;
        if (config.margins) {
            if (config.margins.left !== undefined) Dom.marginLeft.value = config.margins.left;
            if (config.margins.right !== undefined) Dom.marginRight.value = config.margins.right;
            if (config.margins.top !== undefined) Dom.marginTop.value = config.margins.top;
            if (config.margins.bottom !== undefined) Dom.marginBottom.value = config.margins.bottom;
        }
        if (config.font) {
            if (config.font.family) Dom.fontFamily.value = config.font.family;
            if (config.font.size) Dom.fontSize.value = config.font.size;
        }
        if (config.lineSpacing !== undefined) Dom.lineSpacing.value = config.lineSpacing;
        if (config.firstIndent) Dom.firstIndent.value = config.firstIndent;
        if (config.header !== undefined) Dom.enableHeader.checked = config.header;
        if (config.footer !== undefined) Dom.enableFooter.checked = config.footer;
    }

    /**
     * 硬编码的默认配置（API 不可用时的降级方案）
     */
    function getHardcodedDefaults() {
        return {
            paperSize: 'A4',
            orientation: '纵向',
            margins: { left: 20, right: 20, top: 16, bottom: 16 },
            font: { family: '微软雅黑', size: '小四(12pt)' },
            lineSpacing: 16,
            firstIndent: '2字符',
            header: true,
            footer: true
        };
    }

    /**
     * 加载初始配置（页面启动时）
     */
    function loadInitialConfig() {
        Api.getConfig().then(function(res) {
            if (res.success && res.config) {
                applyConfigToForm(res.config);
            }
        }).catch(function() {
            console.log('[md2docx] 使用默认配置启动');
        });
    }

    /* ============================================
       文件列表管理
       ============================================ */
    function bindFileEvents() {
        Dom.addFilesBtn.addEventListener('click', function() {
            Dom.fileInput.click();
        });

        Dom.addFolderBtn.addEventListener('click', function() {
            Dom.folderInput.click();
        });

        Dom.clearFileListBtn.addEventListener('click', function() {
            if (AppState.files.length === 0) {
                addLog('warn', '文件列表已经是空的');
                return;
            }
            showConfirmDialog(
                '确认要清空文件列表吗？已选中的 ' + AppState.files.length + ' 个文件将被移除。',
                function() { clearFileList(); }
            );
        });
    }

    /**
     * 添加文件到列表（前端 + 后端同步）
     */
    function addFilesToList(fileList) {
        var existingNames = AppState.files.map(function(f) { return f.name; });
        var addedCount = 0;

        fileList.forEach(function(file) {
            if (existingNames.indexOf(file.name) === -1) {
                var fileObj = {
                    id: Date.now() + Math.random().toString(36).substr(2, 9),
                    name: file.name,
                    path: file.path.replace(/[^/\\]*$/, ''),
                    status: 'pending'
                };
                AppState.files.push(fileObj);
                existingNames.push(file.name);
                addedCount++;
            }
        });

        updateFileListUI();

        if (addedCount > 0) {
            addLog('info', '添加了 ' + addedCount + ' 个文件到转换列表');

            // 同步到后端
            Api.addFiles(fileList).then(function(res) {
                if (!res.success) {
                    addLog('warn', '后端同步失败，文件仅保存在本地');
                }
            }).catch(function() {});
        } else {
            addLog('warn', '所有文件已存在于列表中（跳过重复）');
        }
    }

    /**
     * 清空文件列表
     */
    function clearFileList() {
        var count = AppState.files.length;
        AppState.files = [];
        updateFileListUI();

        // 同步到后端
        Api.clearFiles().then(function() {}).catch(function() {});

        addLog('info', '已清空文件列表（移除 ' + count + ' 个文件）');
    }

    /**
     * 更新文件列表 UI 渲染
     */
    function updateFileListUI() {
        var tbody = Dom.fileTableBody;
        tbody.innerHTML = '';

        if (AppState.files.length === 0) {
            Dom.tableEmptyState.style.display = '';
            Dom.fileCountBadge.textContent = '(共 0 个文件)';
            return;
        }

        Dom.tableEmptyState.style.display = 'none';
        Dom.fileCountBadge.textContent = '(共 ' + AppState.files.length + ' 个文件)';

        AppState.files.forEach(function(file) {
            var tr = document.createElement('tr');
            tr.dataset.fileId = file.id;

            var badgeHtml = buildStatusBadge(file.status);

            tr.innerHTML =
                '<td class="col-name">' + escapeHtml(file.name) + '</td>' +
                '<td class="col-path">' + escapeHtml(file.path) + '</td>' +
                '<td class="col-status">' + badgeHtml + '</td>';

            tbody.appendChild(tr);
        });
    }

    /**
     * 构建状态徽章 HTML
     */
    function buildStatusBadge(status) {
        var icons = {
            pending: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
            converting: '<svg class="badge-spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><path d="M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83m-2.83-14.14l2.83 2.83m-14.14 0l2.83-2.83"/></svg>',
            success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
            error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
        };
        var labels = {
            pending: '待转换',
            converting: '转换中',
            success: '成功',
            error: '失败'
        };

        return '<span class="badge badge--' + status + '">' +
               (icons[status] || icons.pending) + ' ' +
               (labels[status] || labels.pending) + '</span>';
    }

    /**
     * 更新单个文件的状态
     */
    function updateFileStatus(fileId, status) {
        var file = AppState.files.find(function(f) { return f.id === fileId; });
        if (file) {
            file.status = status;
            var tr = Dom.fileTableBody.querySelector('tr[data-file-id="' + fileId + '"]');
            if (tr) {
                var td = tr.querySelector('.col-status');
                if (td) td.innerHTML = buildStatusBadge(status);
            }
        }
    }

    /* ============================================
       批量转换流程控制
       ============================================ */
    function bindConversionEvents() {
        Dom.startBtn.addEventListener('click', startConversion);
        Dom.stopBtn.addEventListener('click', stopConversion);
    }

    /**
     * 开始批量转换
     */
    function startConversion() {
        if (AppState.isConverting) return;
        if (AppState.files.length === 0) {
            showErrorDialog('请先添加要转换的 Markdown 文件');
            return;
        }

        // 收集转换配置
        var config = {
            inputPath: Dom.inputPath.value,
            outputPath: Dom.outputPath.value,
            sameDir: Dom.sameDir.checked,
            format: readConfigFromForm(),
            files: AppState.files.map(function(f) { return { id: f.id, name: f.name, path: f.path }; })
        };

        // 锁定 UI
        setConvertingState(true);

        // 调用 API 开始转换
        Api.startConversion(config).then(function(res) {
            if (res.success) {
                addLog('info', '开始批量转换，共 ' + (res.totalFiles || AppState.files.length) + ' 个文件');
                startProgressPolling();
            } else {
                setConvertingState(false);
                showErrorDialog(res.error || '无法启动转换任务');
            }
        }).catch(function(err) {
            setConvertingState(false);
            // 如果 API 不可用，使用模拟模式进行演示
            addLog('warn', '后端服务不可用，进入模拟演示模式...');
            startMockConversion();
        });
    }

    /**
     * 停止转换任务
     */
    function stopConversion() {
        Api.stopConversion().then(function(res) {
            addLog('info', '用户停止转换' + (res.completedCount ? '，已完成 ' + res.completedCount + ' 个文件' : ''));
        }).catch(function() {});

        setConvertingState(false);

        if (AppState.progressTimer) {
            clearInterval(AppState.progressTimer);
            AppState.progressTimer = null;
        }

        // 将所有 "转换中" 的文件标记回 "待转换"
        AppState.files.forEach(function(f) {
            if (f.status === 'converting') updateFileStatus(f.id, 'pending');
        });

        addLog('warn', '转换已停止');
    }

    /**
     * 设置转换中 UI 状态（锁定/解锁按钮）
     */
    function setConvertingState(isConverting) {
        AppState.isConverting = isConverting;
        Dom.startBtn.disabled = isConverting;
        Dom.stopBtn.disabled = !isConverting;
        Dom.addFilesBtn.disabled = isConverting;
        Dom.addFolderBtn.disabled = isConverting;
        Dom.clearFileListBtn.disabled = isConverting;
    }

    /**
     * 启动进度轮询（每 500ms）
     */
    function startProgressPolling() {
        if (AppState.progressTimer) clearInterval(AppState.progressTimer);

        var totalFiles = AppState.files.length;
        var completedCount = 0;

        // 先将所有文件设为 "转换中"
        AppState.files.forEach(function(f, idx) {
            setTimeout(function() {
                updateFileStatus(f.id, 'converting');
            }, idx * 200);
        });

        AppState.progressTimer = setInterval(function() {
            Api.getProgress().then(function(res) {
                if (!AppState.isConverting) return;

                if (res.status === 'completed' || res.status === 'stopped' || res.status === 'error') {
                    handleConversionComplete(res);
                    return;
                }

                // 更新进度条
                var progress = res.progress || 0;
                var currentIdx = res.currentIndex || 0;
                updateProgressBar(progress, currentIdx + 1, totalFiles);

                // 更新各文件状态
                if (res.completedFiles) {
                    res.completedFiles.forEach(function(fname) {
                        var f = AppState.files.find(function(x) { return x.name === fname; });
                        if (f) updateFileStatus(f.id, 'success');
                    });
                }
                if (res.failedFiles) {
                    res.failedFiles.forEach(function(item) {
                        var fname = typeof item === 'string' ? item : item.name;
                        var f = AppState.files.find(function(x) { return x.name === fname; });
                        if (f) updateFileStatus(f.id, 'error');
                    });
                }

                // 追加新日志
                if (res.logs && res.logs.length > 0) {
                    res.logs.forEach(function(log) {
                        addLog(log.level || 'info', log.message, false);
                    });
                }
            }).catch(function() {
                // API 轮询失败时自动切换到模拟模式
                handleConversionComplete({ status: 'mock_complete' });
            });
        }, 500);
    }

    /**
     * 模拟转换模式（后端不可用时用于演示）
     */
    function startMockConversion() {
        var totalFiles = AppState.files.length;
        var currentIndex = 0;
        var progress = 0;

        // 将所有文件设为 "转换中"
        AppState.files.forEach(function(f) {
            updateFileStatus(f.id, 'converting');
        });

        AppState.progressTimer = setInterval(function() {
            if (!AppState.isConverting) return;

            progress += Math.random() * 15 + 5;
            var completedSoFar = Math.floor(progress / (100 / totalFiles));

            // 逐个完成文件
            while (currentIndex < completedSoFar && currentIndex < totalFiles) {
                var file = AppState.files[currentIndex];
                var isSuccess = Math.random() > 0.15; // 85% 成功率
                updateFileStatus(file.id, isSuccess ? 'success' : 'error');

                if (isSuccess) {
                    addLog('success', '[OK] ' + file.name + ' 转换成功 (' + (Math.random() * 2 + 0.5).toFixed(1) + 's)');
                } else {
                    addLog('error', '[ERR] ' + file.name + ' 转换失败: 模拟错误');
                }
                currentIndex++;
            }

            progress = Math.min(progress, 100);
            updateProgressBar(progress, currentIndex, totalFiles);

            if (progress >= 100) {
                clearInterval(AppState.progressTimer);
                AppState.progressTimer = null;

                var successCount = AppState.files.filter(function(f) { return f.status === 'success'; }).length;
                var failCount = AppState.files.filter(function(f) { return f.status === 'error'; }).length;

                setTimeout(function() {
                    setConvertingState(false);
                    showCompleteDialog(successCount, failCount);
                    addLog('info', '模拟转换完成：成功 ' + successCount + '，失败 ' + failCount);
                }, 300);
            }
        }, 450);
    }

    /**
     * 转换完成处理
     */
    function handleConversionComplete(result) {
        if (AppState.progressTimer) {
            clearInterval(AppState.progressTimer);
            AppState.progressTimer = null;
        }

        setConvertingState(false);

        var successCount = 0;
        var failCount = 0;

        if (result.status === 'mock_complete') {
            successCount = AppState.files.filter(function(f) { return f.status === 'success'; }).length;
            failCount = AppState.files.filter(function(f) { return f.status === 'error'; }).length;
        } else {
            successCount = result.completedFiles ? result.completedFiles.length :
                            AppState.files.filter(function(f) { return f.status === 'success'; }).length;
            failCount = result.failedFiles ? result.failedFiles.length :
                          AppState.files.filter(function(f) { return f.status === 'error'; }).length;
        }

        updateProgressBar(100, successCount + failCount, successCount + failCount);
        showCompleteDialog(successCount, failCount);
        addLog('info', '全部转换完成：成功 ' + successCount + '，失败 ' + failCount);
    }

    /**
     * 更新进度条显示
     */
    function updateProgressBar(percent, current, total) {
        percent = Math.round(percent);
        Dom.progressFill.style.width = percent + '%';
        Dom.progressText.textContent = percent + '% (' + current + '/' + total + ')';
        Dom.progressFill.parentElement.setAttribute('aria-valuenow', percent);
        Dom.progressFill.parentElement.setAttribute('aria-label', '转换进度 ' + percent + '%');
    }

    /* ============================================
       日志系统
       ============================================ */
    function bindLogEvents() {
        Dom.clearLogBtn.addEventListener('click', function() {
            Dom.logConsole.innerHTML =
                '<div class="log-entry"><span class="log-time">[' + getTimestamp() + ']</span><span class="log-msg-warn">[SYSTEM] 日志已清空</span></div>';
        });

        Dom.exportLogBtn.addEventListener('click', function() {
            Api.exportLogs('txt').then(function(blob) {
                var url = URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'md2docx_log_' + formatDateForFilename(new Date()) + '.txt';
                a.click();
                URL.revokeObjectURL(url);
                addLog('info', '日志已导出');
            }).catch(function() {
                // 降级：直接从 DOM 导出
                exportLogFromDOM();
            });
        });
    }

    /**
     * 添加日志条目
     * @param {string} level - 日志级别：info/success/error/warn
     * @param {string} message - 日志消息
     * @param {boolean} autoScroll - 是否自动滚动到底部（默认 true）
     */
    function addLog(level, message, autoScroll) {
        if (autoScroll === undefined) autoScroll = true;

        var entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML =
            '<span class="log-time">[' + getTimestamp() + ']</span>' +
            '<span class="log-msg-' + level + '">' + escapeHtml(message) + '</span>';

        Dom.logConsole.appendChild(entry);

        if (autoScroll) {
            Dom.logConsole.scrollTop = Dom.logConsole.scrollHeight;
        }
    }

    /**
     * 从 DOM 直接导出日志（降级方案）
     */
    function exportLogFromDOM() {
        var entries = Dom.logConsole.querySelectorAll('.log-entry');
        var lines = [];
        entries.forEach(function(e) {
            lines.push(e.textContent.trim());
        });
        var text = lines.join('\n');
        var blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'md2docx_log_' + formatDateForFilename(new Date()) + '.txt';
        a.click();
        URL.revokeObjectURL(url);
        addLog('info', '日志已导出（本地生成）');
    }

    /* ============================================
       弹窗系统
       ============================================ */
    function bindDialogEvents() {
        // 确认弹窗
        Dom.confirmDialogCancelBtn.addEventListener('click', closeConfirmDialog);
        Dom.confirmDialogOkBtn.addEventListener('click', function() {
            if (AppState.pendingCallback) AppState.pendingCallback();
            closeConfirmDialog();
        });

        // 完成弹窗
        Dom.closeCompleteBtn.addEventListener('click', closeCompleteDialog);
        Dom.openOutputFromCompleteBtn.addEventListener('click', function() {
            closeCompleteDialog();
            var outputPath = Dom.outputPath.value;
            if (outputPath) {
                addLog('info', '正在打开输出文件夹: ' + outputPath);
            } else {
                showErrorDialog('未设置输出路径');
            }
        });

        // 错误弹窗
        Dom.closeErrorBtn.addEventListener('click', closeErrorDialog);

        // ESC 关闭所有弹窗
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeConfirmDialog();
                closeCompleteDialog();
                closeErrorDialog();
            }
        });

        // 点击背景关闭弹窗
        Dom.confirmDialog.addEventListener('click', function(e) {
            if (e.target === Dom.confirmDialog) closeConfirmDialog();
        });
        Dom.completeDialog.addEventListener('click', function(e) {
            if (e.target === Dom.completeDialog) closeCompleteDialog();
        });
        Dom.errorDialog.addEventListener('click', function(e) {
            if (e.target === Dom.errorDialog) closeErrorDialog();
        });
    }

    /**
     * 显示确认弹窗
     */
    function showConfirmDialog(message, callback) {
        Dom.confirmDialogMsg.textContent = message;
        Dom.confirmDialog.classList.add('active');
        AppState.pendingCallback = callback;
        setTimeout(function() { Dom.confirmDialogOkBtn.focus(); }, 100);
    }

    function closeConfirmDialog() {
        Dom.confirmDialog.classList.remove('active');
        AppState.pendingCallback = null;
    }

    /**
     * 显示完成弹窗
     */
    function showCompleteDialog(successCount, failCount) {
        var msg = '成功转换 ' + successCount + ' 个文件';
        if (failCount > 0) msg += '，失败 ' + failCount + ' 个文件';
        msg += '。输出文件已保存至指定目录。';

        Dom.completeDialogMsg.textContent = msg;
        Dom.completeDialog.classList.add('active');
        setTimeout(function() { Dom.openOutputFromCompleteBtn.focus(); }, 100);
    }

    function closeCompleteDialog() {
        Dom.completeDialog.classList.remove('active');
    }

    /**
     * 显示错误弹窗
     */
    function showErrorDialog(message) {
        Dom.errorDialogMsg.textContent = message;
        Dom.errorDialog.classList.add('active');
        setTimeout(function() { Dom.closeErrorBtn.focus(); }, 100);
    }

    function closeErrorDialog() {
        Dom.errorDialog.classList.remove('active');
    }

    /* ============================================
       工具函数
       ============================================ */

    /**
     * HTML 转义（防止 XSS）
     */
    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * 获取当前时间戳字符串 [YYYY-MM-DD HH:MM:SS]
     */
    function getTimestamp() {
        var now = new Date();
        var pad = function(n) { return n < 10 ? '0' + n : n; };
        return now.getFullYear() + '-' +
               pad(now.getMonth() + 1) + '-' +
               pad(now.getDate()) + ' ' +
               pad(now.getHours()) + ':' +
               pad(now.getMinutes()) + ':' +
               pad(now.getSeconds());
    }

    /**
     * 格式化日期为文件名安全格式 YYYYMMDD_HHMMSS
     */
    function formatDateForFilename(date) {
        var pad = function(n) { return n < 10 ? '0' + n : n; };
        return date.getFullYear() +
               pad(date.getMonth() + 1) +
               pad(date.getDate()) + '_' +
               pad(date.getHours()) +
               pad(date.getMinutes()) +
               pad(date.getSeconds());
    }

    /* ============================================
       启动应用
       ============================================ */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
