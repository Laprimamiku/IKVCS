<template>
  <div class="ai-governance-container">
    <div class="header-section">
      <h2>
        <el-icon><Setting /></el-icon>
        智能治理中心
      </h2>
      <p class="subtitle">
        视频是对象、AI是工具、社区是落点。聚焦可量化治理指标与策略演进。
      </p>
    </div>

    <el-tabs v-model="activeTab" class="governance-tabs">
      <el-tab-pane label="治理总览" name="governance">
        <div class="governance-controls">
          <div class="control-left">
            <el-radio-group v-model="governanceDays" size="small" @change="fetchGovernance">
              <el-radio-button :label="7">近7天</el-radio-button>
              <el-radio-button :label="30">近30天</el-radio-button>
              <el-radio-button :label="90">近90天</el-radio-button>
            </el-radio-group>
            <div class="control-item">
              <span class="control-label">视频Top</span>
              <el-input-number
                v-model="governanceLimit"
                :min="5"
                :max="30"
                size="small"
                @change="fetchGovernance"
              />
            </div>
          </div>
          <el-button type="primary" size="small" :loading="governanceLoading" @click="fetchGovernance">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>

        <div v-if="governanceLoading" class="loading-container">
          <el-skeleton :rows="6" animated />
        </div>

        <div v-else class="governance-content">
          <div class="governance-grid">
            <el-card class="score-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>治理总览</span>
                  <el-tag size="small" type="success">{{ governanceWindow }}</el-tag>
                </div>
              </template>
              <div class="score-metrics">
                <div class="score-item">
                  <div class="score-label">治理总分</div>
                  <div class="score-value">{{ overview.governance_score ?? 0 }}</div>
                  <el-progress
                    :percentage="overview.governance_score ?? 0"
                    :color="getScoreColor(overview.governance_score ?? 0)"
                    :stroke-width="8"
                  />
                </div>
                <div class="score-item">
                  <div class="score-label">质量分</div>
                  <div class="score-value">{{ overview.quality_score ?? 0 }}</div>
                  <el-progress
                    :percentage="overview.quality_score ?? 0"
                    :color="getScoreColor(overview.quality_score ?? 0)"
                    :stroke-width="8"
                  />
                </div>
                <div class="score-item">
                  <div class="score-label">风险分</div>
                  <div class="score-value">{{ overview.risk_score ?? 0 }}</div>
                  <el-progress
                    :percentage="overview.risk_score ?? 0"
                    :color="getScoreColor(overview.risk_score ?? 0)"
                    :stroke-width="8"
                  />
                </div>
              </div>
              <div class="score-tags">
                <el-tag>互动量 {{ overview.total_interactions || 0 }}</el-tag>
                <el-tag type="info">AI覆盖 {{ formatPercent(overview.ai_coverage_rate) }}</el-tag>
                <el-tag type="danger">风险率 {{ formatPercent(overview.risk_rate) }}</el-tag>
                <el-tag type="success">高质曝光 {{ formatPercent(overview.highlight_rate) }}</el-tag>
                <el-tag type="warning">低质率 {{ formatPercent(overview.low_quality_rate) }}</el-tag>
                <el-tag type="primary">节省人工 {{ formatPercent(overview.auto_review_saving_rate) }}</el-tag>
              </div>
            </el-card>
            <el-card class="actions-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>治理动作建议</span>
                  <el-icon><InfoFilled /></el-icon>
                </div>
              </template>
              <div v-if="governanceActions.length" class="actions-list">
                <el-alert
                  v-for="(item, idx) in governanceActions"
                  :key="idx"
                  :title="item.title"
                  :description="item.detail"
                  type="warning"
                  :closable="false"
                  show-icon
                />
              </div>
              <el-empty v-else description="暂无动作建议" />
            </el-card>

            <el-card class="distribution-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>质量分布</span>
                  <el-tag size="small" type="info">分桶统计</el-tag>
                </div>
              </template>
              <div class="bucket-list">
                <div class="bucket-row">
                  <span class="bucket-label">0-39</span>
                  <el-progress
                    :percentage="getBucketPercent(distribution['0_39'])"
                    :color="'#F56C6C'"
                    :format="() => `${distribution['0_39'] || 0} 条`"
                  />
                </div>
                <div class="bucket-row">
                  <span class="bucket-label">40-59</span>
                  <el-progress
                    :percentage="getBucketPercent(distribution['40_59'])"
                    :color="'#E6A23C'"
                    :format="() => `${distribution['40_59'] || 0} 条`"
                  />
                </div>
                <div class="bucket-row">
                  <span class="bucket-label">60-79</span>
                  <el-progress
                    :percentage="getBucketPercent(distribution['60_79'])"
                    :color="'#409EFF'"
                    :format="() => `${distribution['60_79'] || 0} 条`"
                  />
                </div>
                <div class="bucket-row">
                  <span class="bucket-label">80-100</span>
                  <el-progress
                    :percentage="getBucketPercent(distribution['80_100'])"
                    :color="'#67C23A'"
                    :format="() => `${distribution['80_100'] || 0} 条`"
                  />
                </div>
              </div>
            </el-card>

            <el-card class="sources-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>模型来源分布</span>
                  <el-tag size="small" type="info">推理来源</el-tag>
                </div>
              </template>
              <div class="sources-list">
                <div v-for="item in sourceList" :key="item.label" class="source-row">
                  <span class="source-label">{{ item.label }}</span>
                  <div class="source-bar">
                    <div class="source-fill" :style="{ width: item.rate + '%' }"></div>
                  </div>
                  <span class="source-value">{{ item.count }}</span>
                </div>
              </div>
            </el-card>
          </div>

          <div class="governance-list-grid">
            <el-card class="risk-table-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>风险优先视频</span>
                  <el-tag type="danger" size="small">AI预警</el-tag>
                </div>
              </template>
              <el-table :data="riskVideos" style="width: 100%" stripe>
                <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
                <el-table-column prop="uploader.nickname" label="作者" width="120" />
                <el-table-column label="风险率" width="100">
                  <template #default="scope">
                    {{ formatPercent(scope.row.metrics?.risk_rate) }}
                  </template>
                </el-table-column>
                <el-table-column label="风险数" width="90">
                  <template #default="scope">
                    {{ scope.row.metrics?.risk_count || 0 }}
                  </template>
                </el-table-column>
                <el-table-column label="治理分" width="90">
                  <template #default="scope">
                    <span :style="{ color: getScoreColor(scope.row.metrics?.governance_score || 0) }">
                      {{ scope.row.metrics?.governance_score || 0 }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <el-card class="highlight-table-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>高质量曝光视频</span>
                  <el-tag type="success" size="small">优先曝光</el-tag>
                </div>
              </template>
              <el-table :data="highlightVideos" style="width: 100%" stripe>
                <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
                <el-table-column prop="uploader.nickname" label="作者" width="120" />
                <el-table-column label="高质率" width="100">
                  <template #default="scope">
                    {{ formatPercent(scope.row.metrics?.highlight_rate) }}
                  </template>
                </el-table-column>
                <el-table-column label="高质数" width="90">
                  <template #default="scope">
                    {{ scope.row.metrics?.highlight_count || 0 }}
                  </template>
                </el-table-column>
                <el-table-column label="治理分" width="90">
                  <template #default="scope">
                    <span :style="{ color: getScoreColor(scope.row.metrics?.governance_score || 0) }">
                      {{ scope.row.metrics?.governance_score || 0 }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>

          <el-card class="ablation-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>消融实验配置（工程复杂度展示）</span>
                <el-tag size="small" type="warning">论文核心</el-tag>
              </div>
            </template>
            <div class="ablation-description">
              <p>系统采用分层架构设计，各模块可独立启用/关闭，便于进行消融实验和性能对比。</p>
            </div>
            <div class="ablation-layers">
              <div class="layer-group">
                <h4>Layer 1: 规则过滤</h4>
                <el-tag
                  v-for="flag in ablationList.filter(f => f.key === 'rule_filter')"
                  :key="flag.label"
                  :type="flag.enabled ? 'success' : 'info'"
                  size="small"
                >
                  {{ flag.label }}: {{ flag.enabled ? '启用' : '关闭' }}
                </el-tag>
              </div>
              <div class="layer-group">
                <h4>Layer 1.5: 缓存层</h4>
                <el-tag
                  v-for="flag in ablationList.filter(f => f.key === 'exact_cache' || f.key === 'semantic_cache')"
                  :key="flag.label"
                  :type="flag.enabled ? 'success' : 'info'"
                  size="small"
                >
                  {{ flag.label }}: {{ flag.enabled ? '启用' : '关闭' }}
                </el-tag>
              </div>
              <div class="layer-group">
                <h4>Layer 2: 模型层</h4>
                <el-tag
                  v-for="flag in ablationList.filter(f => f.key === 'local_model' || f.key === 'cloud_model')"
                  :key="flag.label"
                  :type="flag.enabled ? 'success' : 'info'"
                  size="small"
                >
                  {{ flag.label }}: {{ flag.enabled ? '启用' : '关闭' }}
                </el-tag>
              </div>
              <div class="layer-group">
                <h4>Layer 3: 多智能体</h4>
                <el-tag
                  v-for="flag in ablationList.filter(f => f.key === 'multi_agent')"
                  :key="flag.label"
                  :type="flag.enabled ? 'success' : 'info'"
                  size="small"
                >
                  {{ flag.label }}: {{ flag.enabled ? '启用' : '关闭' }}
                </el-tag>
              </div>
              <div class="layer-group">
                <h4>优化策略</h4>
                <el-tag
                  v-for="flag in ablationList.filter(f => f.key === 'token_saving' || f.key === 'queue_enabled')"
                  :key="flag.label"
                  :type="flag.enabled ? 'success' : 'info'"
                  size="small"
                >
                  {{ flag.label }}: {{ flag.enabled ? '启用' : '关闭' }}
                </el-tag>
              </div>
            </div>
            <div class="thresholds">
              <h4>阈值配置</h4>
              <div class="threshold-grid">
                <div class="threshold-item" v-for="item in thresholdList" :key="item.label">
                  <span class="threshold-label">{{ item.label }}</span>
                  <span class="threshold-value">{{ item.value }}</span>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="Prompt与纠错" name="prompt">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="label">Prompt 版本迭代</div>
            <div class="value">
              {{ totalVersions }} <span class="unit">次</span>
            </div>
            <div class="desc">最近更新 {{ lastUpdateTime }}</div>
          </div>
          <div class="stat-card warning">
            <div class="label">待分析误判</div>
            <div class="value">
              {{ pendingCorrections }} <span class="unit">条</span>
            </div>
            <div class="action">
              <el-button
                type="primary"
                size="small"
                @click="triggerAnalysis"
                :disabled="analyzing"
                :loading="analyzing"
              >
                <el-icon v-if="!analyzing"><MagicStick /></el-icon>
                {{ analyzing ? '分析中...' : '触发元分析' }}
              </el-button>
            </div>
          </div>
          <div class="stat-card">
            <div class="label">人工修正记录</div>
            <div class="value">
              {{ totalCorrections }} <span class="unit">条</span>
            </div>
            <div class="action">
              <el-button type="success" size="small" @click="openCorrectionDialog">
                <el-icon><Edit /></el-icon> 手动修正
              </el-button>
            </div>
          </div>
        </div>
        <el-card class="workflow-card" shadow="hover">
          <div class="workflow-header">
            <div>
              <h3>提示工程工作流</h3>
              <p class="workflow-subtitle">Define → Write → Test → Evaluate → Refine → Ship</p>
            </div>
            <el-tag size="small" type="info">本地/云端统一</el-tag>
          </div>
          <div class="workflow-grid">
            <div class="workflow-block">
              <div class="workflow-title">1. 定义任务</div>
              <el-select v-model="workflowTaskId" size="small" placeholder="选择任务" @change="syncWorkflowTask">
                <el-option
                  v-for="task in workflowTasks"
                  :key="task.id"
                  :label="`${task.name} (${task.prompt_type})`"
                  :value="task.id"
                />
              </el-select>
              <el-input v-model="workflowTaskName" size="small" placeholder="任务名称" />
              <el-input v-model="workflowTaskGoal" type="textarea" :rows="3" placeholder="任务目标" />
              <el-input v-model="workflowTaskMetrics" type="textarea" :rows="2" placeholder="评估指标 (JSON/文本)" />
              <el-button size="small" type="primary" :loading="workflowSaving" @click="saveWorkflowTask">
                保存任务
              </el-button>
            </div>
            <div class="workflow-block">
              <div class="workflow-title">2. 编写Prompt</div>
              <el-select v-model="workflowPromptType" size="small" placeholder="Prompt类型">
                <el-option label="评论区审核" value="COMMENT" />
                <el-option label="弹幕审核" value="DANMAKU" />
                <el-option label="热梗专家" value="MEME_EXPERT" />
                <el-option label="情感专家" value="EMOTION_EXPERT" />
                <el-option label="法律专家" value="LEGAL_EXPERT" />
                <el-option label="裁决者" value="JUDGE_AGENT" />
              </el-select>
              <el-input v-model="workflowDraftPrompt" type="textarea" :rows="6" placeholder="候选Prompt草案" />
              <el-button size="small" type="success" :loading="workflowDraftSaving" @click="createWorkflowDraft">
                保存为候选版本
              </el-button>
            </div>
            <div class="workflow-block">
              <div class="workflow-title">3-4. 测试与评估</div>
              <el-select v-model="workflowCandidateVersionId" size="small" placeholder="选择候选版本">
                <el-option
                  v-for="version in versions.filter(v => !v.is_active)"
                  :key="version.id"
                  :label="`V${version.id} - ${version.update_reason}`"
                  :value="version.id"
                />
              </el-select>
              <div class="workflow-inline">
                <el-input-number v-model="workflowSampleLimit" :min="10" :max="200" size="small" />
                <el-select v-model="workflowModelSource" size="small">
                  <el-option label="自动" value="auto" />
                  <el-option label="本地" value="local" />
                  <el-option label="云端" value="cloud" />
                </el-select>
              </div>
              <el-button size="small" type="primary" :loading="workflowTestLoading" @click="runWorkflowTest">
                运行测试
              </el-button>
              <div v-if="workflowTestResult" class="workflow-metrics">
                <div class="metric-row">
                  <span>一致率</span>
                  <strong>{{ ((workflowTestResult.consistency_rate || 0) * 100).toFixed(1) }}%</strong>
                </div>
                <div class="metric-row">
                  <span>平均分差</span>
                  <strong>{{ (workflowTestResult.avg_score_diff || 0).toFixed(1) }}</strong>
                </div>
                <div class="metric-row">
                  <span>候选命中</span>
                  <strong>{{ ((workflowTestResult.metrics?.candidate?.category_match_rate || 0) * 100).toFixed(1) }}%</strong>
                </div>
                <div class="metric-row">
                  <span>推荐</span>
                  <strong>{{ formatWorkflowAction(workflowTestResult.recommendation?.action) }}</strong>
                </div>
              </div>
            </div>
            <div class="workflow-block">
              <div class="workflow-title">5-6. 迭代与发布</div>
              <el-button size="small" type="warning" :loading="analyzing" @click="triggerAnalysis">
                生成迭代建议
              </el-button>
              <el-button size="small" type="success" @click="publishWorkflowCandidate">
                发布候选版本
              </el-button>
            </div>
          </div>
        </el-card>
        <div class="main-content">
          <div class="panel evolution-panel">
            <div class="panel-header">
              <h3>
                <el-icon><Document /></el-icon>
                Prompt 版本管理
              </h3>
              <el-select v-model="selectedPromptType" @change="fetchVersions" size="small" style="width: 200px;">
                <el-option label="评论区审核" value="COMMENT" />
                <el-option label="弹幕审核" value="DANMAKU" />
                <el-option label="热梗专家" value="MEME_EXPERT" />
                <el-option label="情感专家" value="EMOTION_EXPERT" />
                <el-option label="法律专家" value="LEGAL_EXPERT" />
                <el-option label="裁决者" value="JUDGE_AGENT" />
              </el-select>
            </div>

            <div class="timeline">
              <div
                v-for="version in versions"
                :key="version.id"
                class="timeline-item"
                :class="{ active: selectedVersion?.id === version.id }"
                @click="selectedVersion = version"
              >
                <div class="time">{{ formatDate(version.created_at) }}</div>
                <div class="reason">{{ version.update_reason }}</div>
                <div class="meta">
                  <el-tag v-if="version.is_active" type="success" size="small">激活中</el-tag>
                  <span class="operator">Operator ID: {{ version.updated_by }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="panel detail-panel">
            <div v-if="selectedVersion && !analysisResult && !showShadowTest && !showCostDashboard" class="version-detail">
              <div class="detail-header">
                <h3>版本 V{{ selectedVersion.id }} 详情</h3>
                <div class="actions">
                  <el-button type="primary" size="small" @click="showShadowTest = true">
                    <el-icon><DataAnalysis /></el-icon> Shadow 测试
                  </el-button>
                  <el-button type="info" size="small" @click="showCostDashboard = true">
                    <el-icon><TrendCharts /></el-icon> 成本仪表盘
                  </el-button>
                  <el-switch
                    v-model="showDiff"
                    active-text="Diff 对比"
                    inactive-text="源码模式"
                  />
                  <span class="tag">{{ selectedVersion.prompt_type }}</span>
                </div>
              </div>

              <div class="code-preview" v-if="!showDiff">
                <pre>{{ selectedVersion.prompt_content }}</pre>
              </div>
              <div class="diff-view" v-else>
                <div class="diff-column">
                  <div class="diff-header">上一版本 (V{{ getPreviousVersion(selectedVersion)?.id || 'Null' }})</div>
                  <pre>{{ getPreviousVersion(selectedVersion)?.prompt_content || '// 无上一版本' }}</pre>
                </div>
                <div class="diff-column current">
                  <div class="diff-header">当前版本 (V{{ selectedVersion.id }})</div>
                  <pre>{{ selectedVersion.prompt_content }}</pre>
                </div>
              </div>
            </div>
            <div v-if="showShadowTest" class="shadow-test-view">
              <div class="result-header">
                <h3>
                  <el-icon><DataAnalysis /></el-icon>
                  Shadow 测试
                </h3>
                <el-button type="info" size="small" @click="showShadowTest = false">
                  返回
                </el-button>
              </div>

              <div class="shadow-test-content">
                <div class="test-config">
                  <h4>测试配置</h4>
                  <el-form :model="shadowTestForm" label-width="120px" size="small">
                    <el-form-item label="候选版本">
                      <el-select v-model="shadowTestForm.candidateVersionId" placeholder="选择候选版本">
                        <el-option
                          v-for="version in versions.filter(v => !v.is_active)"
                          :key="version.id"
                          :label="`V${version.id} - ${version.update_reason}`"
                          :value="version.id"
                        />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="测试样本数">
                      <el-input-number v-model="shadowTestForm.sampleLimit" :min="10" :max="200" />
                    </el-form-item>
                    <el-form-item>
                      <el-button type="primary" @click="runShadowTest" :loading="shadowTestLoading">
                        <el-icon><VideoPlay /></el-icon> 运行测试
                      </el-button>
                    </el-form-item>
                  </el-form>
                </div>

                <div v-if="shadowTestResults" class="test-results">
                  <h4>测试结果</h4>
                  <div class="metrics-grid">
                    <div class="metric-card">
                      <div class="metric-label">一致率</div>
                      <div class="metric-value">{{ (shadowTestResults.consistency_rate * 100).toFixed(1) }}%</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-label">平均分差</div>
                      <div class="metric-value">{{ shadowTestResults.avg_score_diff.toFixed(1) }}</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-label">预计成本</div>
                      <div class="metric-value">¥{{ shadowTestResults.estimated_cost.toFixed(3) }}</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-label">样本量</div>
                      <div class="metric-value">{{ shadowTestResults.sample_count }}</div>
                    </div>
                  </div>

                  <div class="test-recommendation">
                    <el-alert
                      :title="getTestRecommendation(shadowTestResults)"
                      :type="getTestRecommendationType(shadowTestResults)"
                      show-icon
                      :closable="false"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div v-if="showCostDashboard" class="cost-dashboard-view">
              <div class="result-header">
                <h3>
                  <el-icon><TrendCharts /></el-icon>
                  成本与性能仪表盘
                </h3>
                <el-button type="info" size="small" @click="showCostDashboard = false">
                  返回
                </el-button>
              </div>

              <div class="dashboard-content">
                <div class="budget-section">
                  <h4>Token 预算状态</h4>
                  <div class="budget-cards">
                    <div class="budget-card">
                      <div class="budget-header">
                        <span>每日预算</span>
                        <el-tag :type="getBudgetTagType(budgetStatus?.daily?.usage_rate || 0)">
                          {{ ((budgetStatus?.daily?.usage_rate || 0) * 100).toFixed(1) }}%
                        </el-tag>
                      </div>
                      <el-progress
                        :percentage="(budgetStatus?.daily?.usage_rate || 0) * 100"
                        :color="getBudgetColor(budgetStatus?.daily?.usage_rate || 0)"
                      />
                      <div class="budget-details">
                        已用: {{ budgetStatus?.daily?.used || 0 }} / {{ budgetStatus?.daily?.limit || 0 }}
                      </div>
                    </div>

                    <div class="budget-card">
                      <div class="budget-header">
                        <span>每小时预算</span>
                        <el-tag :type="getBudgetTagType(budgetStatus?.hourly?.usage_rate || 0)">
                          {{ ((budgetStatus?.hourly?.usage_rate || 0) * 100).toFixed(1) }}%
                        </el-tag>
                      </div>
                      <el-progress
                        :percentage="(budgetStatus?.hourly?.usage_rate || 0) * 100"
                        :color="getBudgetColor(budgetStatus?.hourly?.usage_rate || 0)"
                      />
                      <div class="budget-details">
                        已用: {{ budgetStatus?.hourly?.used || 0 }} / {{ budgetStatus?.hourly?.limit || 0 }}
                      </div>
                    </div>
                  </div>
                </div>

                <div class="metrics-section">
                  <h4>AI 处理命中率统计</h4>
                  <div class="metrics-chart">
                    <div class="chart-item" v-for="(value, key) in aiMetrics" :key="key">
                      <div class="chart-label">{{ getMetricLabel(key) }}</div>
                      <div class="chart-bar">
                        <div
                          class="chart-fill"
                          :style="{ width: getMetricPercentage(key, value) + '%' }"
                        ></div>
                      </div>
                      <div class="chart-value">{{ value }}</div>
                    </div>
                  </div>
                </div>

                <div class="optimization-section">
                  <h4>优化建议</h4>
                  <div class="optimization-cards">
                    <el-card v-for="suggestion in optimizationSuggestions" :key="suggestion.type" class="suggestion-card">
                      <div class="suggestion-header">
                        <el-icon :class="suggestion.icon" />
                        <span>{{ suggestion.title }}</span>
                      </div>
                      <p>{{ suggestion.description }}</p>
                      <div class="suggestion-impact">
                        预计节省: <strong>{{ suggestion.impact }}</strong>
                      </div>
                    </el-card>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="analysisResult" class="analysis-result">
              <div class="result-header">
                <h3>
                  <el-icon><Search /></el-icon>
                  错误模式元分析报告
                </h3>
                <el-button type="info" size="small" @click="analysisResult = null">
                  关闭
                </el-button>
              </div>

              <div class="analysis-content">
                <div class="markdown-body" v-html="renderMarkdown(analysisResult.suggestions)"></div>
              </div>

              <div class="apply-actions">
                <textarea
                  v-model="newPromptDraft"
                  placeholder="在此微调 AI 建议的 Prompt..."
                  class="prompt-editor"
                ></textarea>
                <div class="btn-group">
                  <el-button @click="analysisResult = null">放弃</el-button>
                  <el-button type="primary" @click="applyOptimization">🚀 应用此进化</el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="correctionDialogVisible" title="提交人工修正 (Misjudgment Feedback)" width="500px">
      <el-form :model="correctionForm" label-width="100px">
        <el-form-item label="内容类型">
          <el-radio-group v-model="correctionForm.type">
            <el-radio label="COMMENT">评论</el-radio>
            <el-radio label="DANMAKU">弹幕</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="原始内容">
          <el-input v-model="correctionForm.content" type="textarea" :rows="3" placeholder="输入被误判的内容..." />
        </el-form-item>
        <el-form-item label="原始评分">
          <el-input-number v-model="correctionForm.originalScore" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="正评分">
          <el-input-number v-model="correctionForm.correctedScore" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="修正原因">
          <el-input v-model="correctionForm.reason" placeholder="例如：这是流行梗，非违规" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="correctionDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitCorrection">提交修正</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import {
  Edit,
  Search,
  Setting,
  MagicStick,
  Document,
  DataAnalysis,
  TrendCharts,
  VideoPlay,
  InfoFilled,
  Refresh
} from "@element-plus/icons-vue";
import {
  adminAiApi,
  type PromptVersion,
  type ErrorPatternAnalysis,
  type GovernanceOverview,
  type PromptWorkflowTask
} from "../api/admin.api";
import { formatDate } from "@/shared/utils/formatters";
import { ElMessage } from "element-plus";

const activeTab = ref("governance");

const governanceLoading = ref(false);
const governanceData = ref<GovernanceOverview | null>(null);
const governanceDays = ref(7);
const governanceLimit = ref(10);

const governanceWindow = computed(() => {
  if (!governanceData.value?.window?.start_at) return `近${governanceDays.value}天`;
  return `${governanceData.value.window.start_at} ~ ${governanceData.value.window.end_at}`;
});
const overview = computed(() => governanceData.value?.overview || {});
const distribution = computed(() => governanceData.value?.distribution?.score_buckets || {});
const riskVideos = computed(() => governanceData.value?.videos?.risk || []);
const highlightVideos = computed(() => governanceData.value?.videos?.highlight || []);
const governanceActions = computed(() => governanceData.value?.actions || []);
const ablationFlags = computed(() => governanceData.value?.ablation || {});
const thresholds = computed(() => governanceData.value?.thresholds || {});

const sourceList = computed(() => {
  const sources = governanceData.value?.sources?.distribution || {};
  const total = Object.values(sources).reduce((sum, val) => sum + Number(val || 0), 0);
  return Object.entries(sources)
    .map(([key, value]) => {
      const count = Number(value || 0);
      const rate = total ? Math.round((count / total) * 100) : 0;
      return { key, label: getSourceLabel(key), count, rate };
    })
    .sort((a, b) => b.count - a.count);
});

const ablationList = computed(() => {
  return Object.entries(ablationFlags.value || {}).map(([key, enabled]) => {
    return { key, label: getAblationLabel(key), enabled: Boolean(enabled) };
  });
});

const thresholdList = computed(() => {
  const data = thresholds.value || {};
  const mapping = [
    { key: "risk_score", label: "风险阈值" },
    { key: "severe_risk_score", label: "严重阈值" },
    { key: "low_quality_score", label: "低质阈值" },
    { key: "highlight_score", label: "高质阈值" }
  ];
  return mapping.map(item => ({
    label: item.label,
    value: data[item.key] ?? "-"
  }));
});

const getScoreColor = (score: number) => {
  if (score >= 90) return "#67C23A";
  if (score >= 60) return "#E6A23C";
  return "#F56C6C";
};

const formatPercent = (value?: number) => {
  const safe = Number.isFinite(value) ? value || 0 : 0;
  return `${(safe * 100).toFixed(1)}%`;
};

const getBucketPercent = (val: number) => {
  const total = overview.value?.total_interactions || 0;
  if (!total) return 0;
  return Math.round(((val || 0) / total) * 100);
};

const getSourceLabel = (key: string) => {
  const labels: Record<string, string> = {
    rule_hit: "规则命中",
    cache_exact: "精确缓存",
    cache_semantic: "语义缓存",
    cloud_llm: "云端模型",
    local_model: "本地模型",
    multi_agent: "多智能体",
    default: "默认",
    unknown: "未知"
  };
  return labels[key] || key;
};

const getAblationLabel = (key: string) => {
  const labels: Record<string, string> = {
    rule_filter: "规则过滤",
    exact_cache: "精确缓存",
    semantic_cache: "语义缓存",
    local_model: "本地模型",
    cloud_model: "云端模型",
    multi_agent: "多智能体",
    queue_enabled: "队列分析",
    token_saving: "Token节省"
  };
  return labels[key] || key;
};

const fetchGovernance = async () => {
  governanceLoading.value = true;
  try {
    const res = await adminAiApi.getGovernanceOverview({
      days: governanceDays.value,
      limit: governanceLimit.value
    });
    if (res.success && res.data) {
      governanceData.value = res.data;
    } else {
      ElMessage.warning(res.message || "获取数据失败，可能暂无数据");
      // 设置默认值，避免页面显示错误
      governanceData.value = {
        overview: {},
        distribution: { score_buckets: {} },
        videos: { risk: [], highlight: [] },
        actions: [],
        sources: { distribution: {} },
        ablation: {},
        thresholds: {}
      };
    }
  } catch (e: any) {
    console.error("获取治理总览失败", e);
    ElMessage.error("获取治理总览失败: " + (e.message || "未知错误"));
    // 设置默认值
    governanceData.value = {
      overview: {},
      distribution: { score_buckets: {} },
      videos: { risk: [], highlight: [] },
      actions: [],
      sources: { distribution: {} },
      ablation: {},
      thresholds: {}
    };
  } finally {
    governanceLoading.value = false;
  }
};

const versions = ref<PromptVersion[]>([]);
const totalVersions = ref(0);
const lastUpdateTime = ref("-");
const selectedPromptType = ref("COMMENT");
const selectedVersion = ref<PromptVersion | null>(null);
const showDiff = ref(false);

const pendingCorrections = ref(0);
const totalCorrections = ref(0);
const analyzing = ref(false);
const analysisResult = ref<ErrorPatternAnalysis | null>(null);
const newPromptDraft = ref("");

const showShadowTest = ref(false);
const shadowTestLoading = ref(false);
const shadowTestForm = ref({
  candidateVersionId: null,
  sampleLimit: 50
});
const shadowTestResults = ref(null);

const workflowTasks = ref<PromptWorkflowTask[]>([]);
const workflowTaskId = ref<number | null>(null);
const workflowTaskName = ref("");
const workflowTaskGoal = ref("");
const workflowTaskMetrics = ref("");
const workflowSaving = ref(false);

const workflowPromptType = ref("COMMENT");
const workflowDraftPrompt = ref("");
const workflowDraftSaving = ref(false);

const workflowCandidateVersionId = ref<number | null>(null);
const workflowSampleLimit = ref(50);
const workflowModelSource = ref("auto");
const workflowTestLoading = ref(false);
const workflowTestResult = ref<any | null>(null);

const showCostDashboard = ref(false);
const budgetStatus = ref(null);
const aiMetrics = ref({});
const optimizationSuggestions = ref([
  {
    type: "cache",
    title: "提高缓存命中率",
    description: "当前缓存命中率偏低，建议优化缓存策略以减少重复计算。",
    impact: "30% Token消耗",
    icon: "el-icon-lightning"
  },
  {
    type: "sampling",
    title: "优化采样策略",
    description: "对低风险内容采用更激进的采样策略，减少不必要的分析。",
    impact: "20% 处理时间",
    icon: "el-icon-data-analysis"
  },
  {
    type: "batch",
    title: "启用批量处理",
    description: "将相似内容批量处理，提升API调用效率。",
    impact: "15% API调用",
    icon: "el-icon-collection"
  }
]);

const correctionDialogVisible = ref(false);
const correctionForm = ref({
  type: "COMMENT",
  content: "",
  originalScore: 0,
  correctedScore: 100,
  reason: ""
});

const fetchVersions = async () => {
  try {
    const res = await adminAiApi.getPromptVersions({
      prompt_type: selectedPromptType.value,
      limit: 20
    });

    if (res.success) {
      versions.value = res.data.items;
      totalVersions.value = res.data.total;

      if (versions.value.length > 0) {
        selectedVersion.value = versions.value[0];
        lastUpdateTime.value = formatDate(versions.value[0].created_at);
      }
      const candidate = versions.value.find(v => !v.is_active);
      if (candidate) {
        workflowCandidateVersionId.value = candidate.id;
      }
    }
  } catch (e) {
    console.error("加载版本失败", e);
  }
};

const fetchWorkflowTasks = async () => {
  try {
    const res = await adminAiApi.getPromptWorkflowTasks();
    if (res.success) {
      workflowTasks.value = res.data.items || [];
      if (!workflowTaskId.value && workflowTasks.value.length > 0) {
        workflowTaskId.value = workflowTasks.value[0].id;
        syncWorkflowTask();
      }
    }
  } catch (e) {
    console.error("加载工作流任务失败", e);
  }
};

const syncWorkflowTask = () => {
  const task = workflowTasks.value.find(item => item.id === workflowTaskId.value);
  if (!task) return;
  workflowTaskName.value = task.name || "";
  workflowTaskGoal.value = task.goal || "";
  workflowTaskMetrics.value = task.metrics ? JSON.stringify(task.metrics, null, 2) : "";
  workflowPromptType.value = task.prompt_type || selectedPromptType.value;
};

const parseWorkflowMetrics = (value: string) => {
  if (!value) return {};
  try {
    return JSON.parse(value);
  } catch {
    return { notes: value };
  }
};

const saveWorkflowTask = async () => {
  if (!workflowTaskName.value) {
    ElMessage.warning("请填写任务名称");
    return;
  }
  workflowSaving.value = true;
  try {
    const currentTask = workflowTasks.value.find(item => item.id === workflowTaskId.value);
    const payload = {
      name: workflowTaskName.value,
      prompt_type: workflowPromptType.value,
      goal: workflowTaskGoal.value,
      metrics: parseWorkflowMetrics(workflowTaskMetrics.value),
      dataset_source: currentTask?.dataset_source || "corrections",
      sample_min: currentTask?.sample_min || 20,
      is_active: currentTask?.is_active ?? true
    };
    if (workflowTaskId.value) {
      await adminAiApi.updatePromptWorkflowTask(workflowTaskId.value, payload);
    } else {
      const res = await adminAiApi.createPromptWorkflowTask(payload);
      if (res.success) {
        workflowTaskId.value = res.data.id;
      }
    }
    ElMessage.success("任务已保存");
    await fetchWorkflowTasks();
  } catch (e) {
    ElMessage.error("任务保存失败");
  } finally {
    workflowSaving.value = false;
  }
};

const createWorkflowDraft = async () => {
  if (!workflowDraftPrompt.value) {
    ElMessage.warning("请输入Prompt草案");
    return;
  }
  workflowDraftSaving.value = true;
  try {
    await adminAiApi.createPromptDraft({
      prompt_type: workflowPromptType.value,
      draft_content: workflowDraftPrompt.value,
      sample_ids: [],
      risk_notes: [],
      expected_impact: ""
    });
    ElMessage.success("候选版本已保存");
    workflowDraftPrompt.value = "";
    fetchVersions();
  } catch (e) {
    ElMessage.error("候选版本保存失败");
  } finally {
    workflowDraftSaving.value = false;
  }
};

const runWorkflowTest = async () => {
  if (!workflowCandidateVersionId.value) {
    ElMessage.warning("请选择候选版本");
    return;
  }
  workflowTestLoading.value = true;
  try {
    const currentTask = workflowTasks.value.find(item => item.id === workflowTaskId.value);
    const res = await adminAiApi.runPromptWorkflowTest({
      candidate_version_id: workflowCandidateVersionId.value,
      sample_limit: workflowSampleLimit.value,
      model_source: workflowModelSource.value,
      dataset_source: currentTask?.dataset_source,
      task_id: workflowTaskId.value || undefined
    });
    if (res.success) {
      workflowTestResult.value = res.data;
      ElMessage.success("测试完成");
    }
  } catch (e) {
    ElMessage.error("测试失败");
  } finally {
    workflowTestLoading.value = false;
  }
};

const publishWorkflowCandidate = async () => {
  if (!workflowCandidateVersionId.value) {
    ElMessage.warning("请选择候选版本");
    return;
  }
  try {
    await adminAiApi.publishPrompt({ version_id: workflowCandidateVersionId.value });
    ElMessage.success("候选版本已发布");
    fetchVersions();
  } catch (e) {
    ElMessage.error("发布失败");
  }
};

const fetchCorrectionsSummary = async () => {
  try {
    const res = await adminAiApi.getCorrections({ page: 1, page_size: 1 });
    if (res.success) {
      totalCorrections.value = res.data.total || 0;
      pendingCorrections.value = res.data.total || 0;
    }
  } catch (e) {
    console.error("加载修正记录失败", e);
  }
};

const getPreviousVersion = (current: PromptVersion) => {
  const index = versions.value.findIndex(v => v.id === current.id);
  if (index !== -1 && index + 1 < versions.value.length) {
    return versions.value[index + 1];
  }
  return null;
};

const triggerAnalysis = async () => {
  analyzing.value = true;
  try {
    const res = await adminAiApi.analyzeErrors({
      days: 7,
      content_type: selectedPromptType.value
    });

    if (res.success) {
      analysisResult.value = res.data;
      newPromptDraft.value =
        extractCodeBlock(res.data.suggestions) ||
        "无法自动提取 Prompt 代码，请手动复制建议内容。";
    }
  } catch (e: unknown) {
    ElMessage.error("分析失败：" + (e.message || "未知错误"));
  } finally {
    analyzing.value = false;
  }
};

const applyOptimization = async () => {
  if (!newPromptDraft.value) return;
  if (!confirm("确定要更新线上 System Prompt 吗？此操作将记录在版本历史中。"))
    return;

  try {
    await adminAiApi.updatePrompt({
      prompt_type: selectedPromptType.value,
      new_prompt: newPromptDraft.value,
      update_reason:
        "基于元分析报告的自动进化 (v" + (totalVersions.value + 1) + ")"
    });
    ElMessage.success("更新成功！系统已进化。");
    analysisResult.value = null;
    fetchVersions();
  } catch (e) {
    ElMessage.error("更新失败");
  }
};

const runShadowTest = async () => {
  if (!shadowTestForm.value.candidateVersionId) {
    ElMessage.warning("请选择候选版本");
    return;
  }

  shadowTestLoading.value = true;
  try {
    const res = await adminAiApi.shadowTestPrompt({
      candidate_version_id: shadowTestForm.value.candidateVersionId,
      sample_limit: shadowTestForm.value.sampleLimit
    });

    if (res.success) {
      shadowTestResults.value = res.data;
      ElMessage.success("Shadow测试完成");
    }
  } catch (e) {
    ElMessage.error("Shadow测试失败");
  } finally {
    shadowTestLoading.value = false;
  }
};
const getTestRecommendation = (results) => {
  const consistencyRate = results.consistency_rate;
  const avgDiff = results.avg_score_diff;

  if (consistencyRate > 0.9 && avgDiff < 5) {
    return "建议发布：候选版本表现优秀，与当前版本高度一致。";
  } else if (consistencyRate > 0.8 && avgDiff < 10) {
    return "谨慎发布：候选版本表现良好，但存在一定差异，建议进一步测试。";
  } else {
    return "不建议发布：候选版本与当前版本差异较大，需要进一步优化。";
  }
};

const getTestRecommendationType = (results) => {
  const consistencyRate = results.consistency_rate;
  if (consistencyRate > 0.9) return "success";
  if (consistencyRate > 0.8) return "warning";
  return "error";
};

const formatWorkflowAction = (action?: string) => {
  if (!action) return "-";
  if (action === "publish") return "发布";
  if (action === "monitor") return "观测";
  if (action === "refine") return "继续优化";
  return action;
};

const fetchBudgetStatus = async () => {
  try {
    budgetStatus.value = {
      daily: { used: 650, limit: 1000, usage_rate: 0.65 },
      hourly: { used: 45, limit: 100, usage_rate: 0.45 }
    };
  } catch (e) {
    console.error("获取预算状态失败", e);
  }
};

const fetchAiMetrics = async () => {
  try {
    const res = await adminAiApi.getAiMetrics();
    if (res.success) {
      aiMetrics.value = res.data.metrics;
    }
  } catch (e) {
    console.error("获取AI指标失败", e);
  }
};

const getBudgetTagType = (rate) => {
  if (rate > 0.8) return "danger";
  if (rate > 0.6) return "warning";
  return "success";
};

const getBudgetColor = (rate) => {
  if (rate > 0.8) return "#f56c6c";
  if (rate > 0.6) return "#e6a23c";
  return "#67c23a";
};

const getMetricLabel = (key) => {
  const labels = {
    rule_hit: "规则命中",
    exact_hit: "精确缓存",
    semantic_hit: "语义缓存",
    cloud_call: "云端调用",
    local_call: "本地调用",
    jury_call: "陪审团调用"
  };
  return labels[key] || key;
};

const getMetricPercentage = (key, value) => {
  const total = Object.values(aiMetrics.value).reduce((sum, val) => sum + val, 0);
  return total > 0 ? (value / total * 100) : 0;
};

const openCorrectionDialog = () => {
  correctionDialogVisible.value = true;
};

const submitCorrection = async () => {
  try {
    const originalScore = Number(correctionForm.value.originalScore) || 0;
    const correctedScore = Number(correctionForm.value.correctedScore) || 0;
    await adminAiApi.submitCorrection({
      content_type: correctionForm.value.type.toLowerCase(),
      content: correctionForm.value.content,
      original_result: {
        score: originalScore,
        category: "manual",
        label: "manual",
        reason: "manual correction",
        is_highlight: originalScore >= 85,
        is_inappropriate: originalScore < 40
      },
      corrected_result: {
        score: correctedScore,
        category: "manual",
        label: "manual",
        reason: correctionForm.value.reason,
        is_highlight: correctedScore >= 85,
        is_inappropriate: correctedScore < 40
      },
      correction_reason: correctionForm.value.reason
    });
    ElMessage.success("修正已提交！系统将在下次元分析时学习此案例。");
    correctionDialogVisible.value = false;
    totalCorrections.value++;
    correctionForm.value = {
      type: "COMMENT",
      content: "",
      originalScore: 0,
      correctedScore: 100,
      reason: ""
    };
  } catch (e) {
    ElMessage.error("提交失败");
  }
};

const renderMarkdown = (text: string) => {
  if (!text) return "";
  return text.replace(/\n/g, "<br>").replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");
};

const extractCodeBlock = (text: string) => {
  if (!text) return "";
  const match = text.match(/```.*?\n([\s\S]*?)```/);
  return match ? match[1] : "";
};

watch(workflowPromptType, (value) => {
  if (value && selectedPromptType.value !== value) {
    selectedPromptType.value = value;
    fetchVersions();
  }
});

watch(selectedPromptType, (value) => {
  if (!workflowTaskId.value) {
    workflowPromptType.value = value;
  }
});

onMounted(() => {
  fetchGovernance();
  fetchVersions();
  fetchWorkflowTasks();
  fetchCorrectionsSummary();
  fetchBudgetStatus();
  fetchAiMetrics();
});
</script>

<style scoped lang="scss">
.ai-governance-container {
  padding: var(--space-6);
  background: var(--bg-global);
  min-height: 100vh;
}

.header-section {
  margin-bottom: var(--space-6);
  h2 {
    font-size: var(--font-size-2xl);
    margin-bottom: var(--space-2);
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
  .subtitle {
    color: var(--text-secondary);
  }
}

.governance-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
  gap: 12px;

  .control-left {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .control-item {
    display: flex;
    align-items: center;
    gap: 8px;

    .control-label {
      font-size: 12px;
      color: var(--text-tertiary);
    }
  }
}

.governance-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
  
  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.score-card {
  grid-column: 1 / 2;
}

.score-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.score-item {
  background: var(--bg-gray-1);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.score-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.score-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.score-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.actions-card,
.distribution-card,
.sources-card {
  grid-column: 2 / 3;
  
  @media (max-width: 1200px) {
    grid-column: 1 / -1;
  }
}

.actions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bucket-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bucket-row {
  display: grid;
  grid-template-columns: 60px 1fr;
  align-items: center;
  gap: 8px;
}

.bucket-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-row {
  display: grid;
  grid-template-columns: 90px 1fr 50px;
  align-items: center;
  gap: 8px;
}

.source-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.source-bar {
  height: 10px;
  background: var(--bg-gray-1);
  border-radius: 6px;
  overflow: hidden;
}

.source-fill {
  height: 100%;
  background: linear-gradient(90deg, #409EFF, #67C23A);
  border-radius: 6px;
}

.source-value {
  text-align: right;
  font-size: 12px;
  color: var(--text-secondary);
}

.governance-list-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 20px;
  
  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
}

.ablation-card {
  margin-bottom: 20px;
}

.ablation-description {
  margin-bottom: 20px;
  padding: 12px;
  background: var(--bg-gray-1);
  border-radius: 8px;

  p {
    margin: 0;
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
  }
}

.ablation-layers {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;

  .layer-group {
    padding: 12px;
    background: var(--bg-gray-1);
    border-radius: 8px;
    border-left: 3px solid var(--primary-color);

    h4 {
      margin: 0 0 8px 0;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .el-tag {
      margin-right: 8px;
      margin-bottom: 4px;
    }
  }
}

.thresholds {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);

  h4 {
    margin: 0 0 12px 0;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.threshold-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.threshold-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-gray-1);
  border-radius: 8px;
  font-size: 12px;
}

.threshold-label {
  color: var(--text-tertiary);
}

.threshold-value {
  font-weight: 600;
  color: var(--text-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);

  .stat-card {
    background: var(--bg-white);
    padding: var(--space-5);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-card);
    transition: transform 0.2s, box-shadow 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    &.warning {
      border-left: 4px solid var(--warning-color);
    }

    .label {
      font-size: var(--font-size-sm);
      color: var(--text-tertiary);
      margin-bottom: var(--space-2);
      font-weight: var(--font-weight-medium);
    }
    .value {
      font-size: var(--font-size-3xl);
      font-weight: var(--font-weight-bold);
      color: var(--text-primary);
      margin-bottom: var(--space-2);
    }
    .unit {
      font-size: var(--font-size-sm);
      font-weight: normal;
      color: var(--text-secondary);
    }
    .desc {
      font-size: 12px;
      color: var(--text-tertiary);
      margin-top: var(--space-2);
    }

    .action {
      margin-top: var(--space-3);
    }
  }
}

.workflow-card {
  margin-bottom: var(--space-6);
  padding: var(--space-4);
}

.workflow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);

  h3 {
    margin: 0;
    font-size: var(--font-size-lg);
    color: var(--text-primary);
  }

  .workflow-subtitle {
    margin: 4px 0 0;
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.workflow-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg-gray-1);
  padding: 12px;
  border-radius: 10px;
}

.workflow-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.workflow-inline {
  display: flex;
  gap: 8px;
  align-items: center;
}

.workflow-metrics {
  background: var(--bg-white);
  border-radius: 8px;
  padding: 8px 10px;
  display: grid;
  gap: 6px;
  font-size: 12px;

  .metric-row {
    display: flex;
    justify-content: space-between;
  }
}

.main-content {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 24px;
  min-height: 600px;
}

.panel {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .panel-header {
    padding: var(--space-4);
    border-bottom: 1px solid var(--border-light);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-hover);

    h3 {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      margin: 0;
      font-size: var(--font-size-lg);
      font-weight: var(--font-weight-semibold);
      color: var(--text-primary);
    }
  }
}
.evolution-panel {
  .timeline {
    flex: 1;
    overflow-y: auto;
    padding: 16px;

    .timeline-item {
      padding: var(--space-3);
      border-left: 3px solid var(--border-color);
      margin-left: var(--space-2);
      position: relative;
      cursor: pointer;
      transition: all 0.2s;
      border-radius: var(--radius-sm);
      margin-bottom: var(--space-2);

      &:hover {
        background: var(--bg-hover);
        border-left-color: var(--primary-color);
      }
      &.active {
        border-left-color: var(--primary-color);
        background: var(--bg-primary-light);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
      }

      &::before {
        content: "";
        position: absolute;
        left: -6px;
        top: 20px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--border-color);
        border: 2px solid white;
        transition: all 0.2s;
      }
      &.active::before {
        background: var(--primary-color);
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(118, 75, 162, 0.2);
      }

      .time {
        font-size: var(--font-size-xs);
        color: var(--text-tertiary);
        margin-bottom: var(--space-1);
      }
      .reason {
        font-size: var(--font-size-sm);
        margin: var(--space-1) 0;
        font-weight: var(--font-weight-medium);
        color: var(--text-primary);
      }
      .meta {
        font-size: var(--font-size-xs);
        color: var(--text-tertiary);
        margin-top: var(--space-1);
      }
    }
  }
}

.detail-panel {
  .version-detail,
  .analysis-result {
    padding: 24px;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .detail-header,
  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .actions {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .tag {
      background: #e0e7ff;
      color: #4338ca;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
    }
  }

  .code-preview {
    flex: 1;
    background: #2d2d2d;
    color: #ccc;
    padding: 16px;
    border-radius: 8px;
    overflow: auto;
    pre {
      margin: 0;
      font-family: monospace;
      white-space: pre-wrap;
    }
  }

  .diff-view {
    flex: 1;
    display: flex;
    gap: 12px;
    overflow: hidden;

    .diff-column {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: #f8f9fa;
      border: 1px solid #ddd;
      border-radius: 6px;
      overflow: hidden;

      &.current {
        background: #fff;
        border-color: #764ba2;
      }

      .diff-header {
        padding: 8px;
        background: #eee;
        font-size: 12px;
        font-weight: bold;
        border-bottom: 1px solid #ddd;
      }

      pre {
        flex: 1;
        margin: 0;
        padding: 12px;
        overflow: auto;
        font-size: 12px;
        white-space: pre-wrap;
        font-family: monospace;
      }
    }
  }

  .analysis-content {
    flex: 1;
    overflow-y: auto;
    border: 1px solid #eee;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 16px;
  }

  .prompt-editor {
    width: 100%;
    height: 150px;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 12px;
    font-family: monospace;
    margin-bottom: 12px;
  }

  .btn-group {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }
}

.shadow-test-view {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;

  .test-config {
    margin-bottom: 24px;
    padding: 16px;
    background: var(--bg-gray-1);
    border-radius: 8px;

    h4 {
      margin: 0 0 16px 0;
      color: var(--text-primary);
    }
  }

  .test-results {
    flex: 1;

    h4 {
      margin: 0 0 16px 0;
      color: var(--text-primary);
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
      margin-bottom: 20px;

      .metric-card {
        background: white;
        padding: 16px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

        .metric-label {
          font-size: 12px;
          color: var(--text-tertiary);
          margin-bottom: 8px;
        }

        .metric-value {
          font-size: 24px;
          font-weight: bold;
          color: var(--text-primary);
        }
      }
    }

    .test-recommendation {
      margin-top: 16px;
    }
  }
}

.cost-dashboard-view {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;

  .dashboard-content {
    flex: 1;

    h4 {
      margin: 0 0 16px 0;
      color: var(--text-primary);
      font-size: 16px;
    }
  }

  .budget-section {
    margin-bottom: 32px;

    .budget-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;

      .budget-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

        .budget-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;

          span {
            font-weight: 600;
            color: var(--text-primary);
          }
        }

        .budget-details {
          margin-top: 8px;
          font-size: 12px;
          color: var(--text-tertiary);
        }
      }
    }
  }

  .metrics-section {
    margin-bottom: 32px;

    .metrics-chart {
      background: white;
      padding: 20px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);

      .chart-item {
        display: flex;
        align-items: center;
        margin-bottom: 16px;

        &:last-child {
          margin-bottom: 0;
        }

        .chart-label {
          width: 100px;
          font-size: 14px;
          color: var(--text-secondary);
        }

        .chart-bar {
          flex: 1;
          height: 20px;
          background: var(--bg-gray-1);
          border-radius: 10px;
          margin: 0 16px;
          position: relative;
          overflow: hidden;

          .chart-fill {
            height: 100%;
            background: linear-gradient(90deg, #409EFF, #67C23A);
            border-radius: 10px;
            transition: width 0.3s ease;
          }
        }

        .chart-value {
          width: 60px;
          text-align: right;
          font-weight: 600;
          color: var(--text-primary);
        }
      }
    }
  }

  .optimization-section {
    .optimization-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;

      .suggestion-card {
        .suggestion-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
          font-weight: 600;
          color: var(--text-primary);
        }

        p {
          margin: 0 0 12px 0;
          color: var(--text-secondary);
          line-height: 1.5;
        }

        .suggestion-impact {
          font-size: 12px;
          color: var(--success-color);

          strong {
            color: var(--success-color);
          }
        }
      }
    }
  }
}

@media (max-width: 1024px) {
  .governance-grid,
  .governance-list-grid {
    grid-template-columns: 1fr;
  }

  .score-metrics {
    grid-template-columns: 1fr;
  }

  .main-content {
    grid-template-columns: 1fr;
  }
}
</style>
