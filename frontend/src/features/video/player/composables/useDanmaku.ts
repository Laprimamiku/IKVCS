import { ref, watch, onBeforeUnmount, type Ref } from 'vue'
import { getDanmakus, sendDanmaku } from "@/features/video/player/api/danmaku.api"
import type { Danmaku, DanmakuDisplayItem } from "@/shared/types/entity"

interface UseDanmakuOptions {
  currentUserId?: Ref<number | null>
  currentTime: Ref<number>
}

export const DANMAKU_DURATION = 10000 
const MAX_LANES = 10 

export function useDanmaku(videoId: Ref<number | null>, options: UseDanmakuOptions) {
  const { currentUserId, currentTime } = options

  const historyList = ref<Danmaku[]>([])
  const activeList = ref<DanmakuDisplayItem[]>([])
  const historyIndex = ref(0)
  const wsRef = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const loadingHistory = ref(false)
  const lastTimeRef = ref(0)
  // 轨道占用情况：记录每个轨道上最后一条弹幕的结束时间
  const laneOccupiedUntil = ref<number[]>(new Array(MAX_LANES).fill(0))
  
  const colorPreset = ['#ffffff', '#fe0302', '#ff7204', '#ffc402', '#00eaff', '#89d519']

  const buildWsUrl = (id: number) => {
    // 优先使用 WebSocket 专用环境变量
    const wsBase = import.meta.env.VITE_WS_BASE_URL;
    if (wsBase) {
      return `${wsBase.replace(/\/$/, '')}/ws/videos/${id}`;
    }
    
    // 从 HTTP API URL 推导 WebSocket URL
    const httpBase = import.meta.env.VITE_API_BASE_URL;
    if (httpBase) {
      const wsUrl = httpBase.replace(/^http/, 'ws');
      return `${wsUrl.replace(/\/$/, '')}/ws/videos/${id}`;
    }
    
    // 开发环境默认值（生产环境必须配置环境变量）
    if (import.meta.env.DEV) {
      return `ws://localhost:8000/api/v1/ws/videos/${id}`;
    }
    
    throw new Error('VITE_API_BASE_URL 或 VITE_WS_BASE_URL 环境变量未配置');
  }

  const loadHistory = async (id: number) => {
    loadingHistory.value = true
    try {
      const res = await getDanmakus(id)
      if (res.success && Array.isArray(res.data)) {
        historyList.value = res.data
          .map((d) => ({
            ...d,
            is_me: currentUserId?.value ? d.user_id === currentUserId.value : false
          }))
          .sort((a, b) => a.video_time - b.video_time)
        
        handleTimeChange(currentTime.value, true)
      }
    } finally {
      loadingHistory.value = false
    }
  }

  const connect = (id: number) => {
    if (wsRef.value) wsRef.value.close()
    const ws = new WebSocket(buildWsUrl(id))
    wsRef.value = ws
    ws.onopen = () => { isConnected.value = true }
    ws.onclose = () => { isConnected.value = false; wsRef.value = null }
    ws.onerror = () => { isConnected.value = false }
    
    // [Fix]: 修改 WebSocket 消息处理逻辑
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // --- 核心修复开始 ---
        // 判断消息是否来自当前用户
        // 如果 WebSocket 推送的 user_id 等于当前登录用户的 ID，说明是自己发的
        // 因为 send() 方法里已经做过本地回显 (enqueue)，所以这里直接忽略，防止重复
        const curId = currentUserId?.value
        if (curId && data.user_id === curId) {
          return
        }
        // --- 核心修复结束 ---

        enqueue(data.text || data.content, data.color || '#ffffff')
      } catch (e) { 
        console.warn('解析弹幕消息失败', e) 
      }
    }
  }

  const disconnect = () => {
    wsRef.value?.close()
    wsRef.value = null
  }

  /**
   * 智能分配轨道，避免弹幕覆盖
   * 当弹幕数量少时，优先使用空闲轨道；当弹幕数量多时，允许覆盖
   */
  const findAvailableLane = (): number => {
    const now = Date.now()
    const activeCount = activeList.value.length
    
    // 如果弹幕数量较少（少于轨道数的2倍），尝试找到空闲轨道
    if (activeCount < MAX_LANES * 2) {
      // 查找空闲轨道（最后一条弹幕已结束）
      for (let i = 0; i < MAX_LANES; i++) {
        if (laneOccupiedUntil.value[i] <= now) {
          // 更新轨道占用时间（弹幕持续时间）
          laneOccupiedUntil.value[i] = now + DANMAKU_DURATION
          return i
        }
      }
    }
    
    // 如果所有轨道都被占用，或弹幕数量很多，随机分配
    const lane = Math.floor(Math.random() * MAX_LANES)
    laneOccupiedUntil.value[lane] = now + DANMAKU_DURATION
    return lane
  }

  // 修改 enqueue 方法，增加 extra 参数来接收 AI 字段和视频时间
  const enqueue = (
    text: string, 
    color = '#ffffff', 
    initialOffset = 0,
    extra: { ai_score?: number; is_highlight?: boolean; id?: number; videoTime?: number } = {} // [New] 添加videoTime字段
  ) => {
    const lane = findAvailableLane()
    const item: DanmakuDisplayItem = {
      key: `${Date.now()}-${Math.random()}`,
      text,
      color,
      lane,
      initialOffset,
      videoTime: extra.videoTime, // [New] 保存原始视频时间
      ...extra // [New] 注入 AI 字段和id
    }
    activeList.value.push(item)
  }

  // 修改 handleTimeChange，在从历史记录加载弹幕时传递 extra 信息
const handleTimeChange = (time: number, forceSeek = false) => {
    const timeDiff = Math.abs(time - lastTimeRef.value)
    const isSeek = forceSeek || timeDiff > 1.5

    if (isSeek) {
      // 清空当前显示的弹幕
      activeList.value = []
      // 重新计算 historyIndex
      const newIndex = historyList.value.findIndex(d => d.video_time >= time)
      historyIndex.value = newIndex === -1 ? historyList.value.length : newIndex

      const durationSec = DANMAKU_DURATION / 1000
      const startTimeWindow = time - durationSec
      
      // 加载当前时间窗口内的弹幕（向前查找）
      let backIndex = historyIndex.value - 1
      while (backIndex >= 0) {
        const item = historyList.value[backIndex]
        if (item.video_time < startTimeWindow) break 
        const elapsed = (time - item.video_time) * 1000
        
        // [修改点 1] 传递 AI 字段 (ai_score, is_highlight) 和 id，以及原始视频时间
        enqueue(item.content, item.color, elapsed, {
          ai_score: item.ai_score,
          is_highlight: item.is_highlight,
          id: item.id,
          videoTime: item.video_time // [New] 保存原始视频时间
        })
        
        backIndex--
      }

      // 确保后续正常播放时能继续加载弹幕
      // 重置 lastTimeRef 为当前时间，避免下次被误判为 seek
      lastTimeRef.value = time
    } else {
      const list = historyList.value
      while (historyIndex.value < list.length && list[historyIndex.value].video_time <= time) {
        const item = list[historyIndex.value]
        
        // [修改点 2] 正常播放时也传递 AI 字段和 id，以及原始视频时间
        // 注意：第3个参数 initialOffset 传 0
        enqueue(item.content, item.color, 0, {
          ai_score: item.ai_score,
          is_highlight: item.is_highlight,
          id: item.id,
          videoTime: item.video_time // [New] 保存原始视频时间
        })
        
        historyIndex.value += 1
      }
      lastTimeRef.value = time
    }
  }

  watch(currentTime, (t) => handleTimeChange(t))

  watch(videoId, (id) => {
    if (id) {
      activeList.value = []
      lastTimeRef.value = 0
      historyIndex.value = 0
      loadHistory(id)
      connect(id)
    } else {
      disconnect()
    }
  }, { immediate: true })

  onBeforeUnmount(() => disconnect())

  return {
    colorPreset,
    activeList,
    isConnected,
    loadingHistory,
    send: async (content: string, color: string, time: number) => {
      if (!videoId.value) return
      // 这里的 API 请求
      const res = await sendDanmaku(videoId.value, { content, color, video_time: time })
      if (res.success && res.data) {
        // [注意]: 这里做了本地回显（立即显示）
        // 所以如果不拦截 WebSocket 推送的自己发的消息，就会导致屏幕上出现两条
        enqueue(res.data.content, res.data.color, 0, {
          id: res.data.id,
          ai_score: res.data.ai_score,
          is_highlight: res.data.is_highlight,
          videoTime: time // [New] 保存发送时的视频时间
        })
      }
      return res
    },
    finishItem: (key: string) => {
      activeList.value = activeList.value.filter((i) => i.key !== key)
    }
  }
}