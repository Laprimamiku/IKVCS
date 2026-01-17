<template>
  <div class="bili-profile-space">
    <AppHeader />

    <!-- Banner Section -->
    <div class="profile-banner">
      <div class="banner-bg"></div>
      <div class="banner-overlay"></div>
      
      <div class="banner-content">
        <!-- User Card -->
        <div class="user-card">
          <div class="avatar-wrapper">
            <img 
              :src="userStore.avatar || '/default-avatar.png'" 
              alt="avatar" 
              class="user-avatar"
            />
          </div>
          
          <div class="user-info">
            <div class="name-row">
              <h1 class="nickname">{{ displayUser.nickname }}</h1>
              <span class="vip-badge" v-if="false">大会员</span>
            </div>
            
            <p class="user-bio">
              {{ displayUser.intro || "这个人很懒，什么都没有写~" }}
            </p>
            
            <div class="user-stats">
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(userStats.following_count) }}</span>
                <span class="stat-label">关注</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(userStats.followers_count) }}</span>
                <span class="stat-label">粉丝</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(userStats.total_likes) }}</span>
                <span class="stat-label">获赞</span>
              </div>
            </div>
          </div>
          
          <div class="action-buttons">
            <el-button class="edit-btn" @click="editVisible = true">
              <el-icon class="btn-icon"><Edit /></el-icon>
              编辑资料
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="profile-nav">
      <div class="nav-container">
        <div class="nav-tabs">
          <div 
            class="nav-tab" 
            :class="{ active: activeTab === 'home' }"
            @click="activeTab = 'home'"
          >
            <el-icon class="tab-icon"><HomeFilled /></el-icon>
            <span class="tab-text">主页</span>
          </div>
          <div 
            class="nav-tab"
            :class="{ active: activeTab === 'videos' }"
            @click="activeTab = 'videos'"
          >
            <el-icon class="tab-icon"><VideoCamera /></el-icon>
            <span class="tab-text">投稿</span>
            <span class="tab-count">{{ videos.length }}</span>
          </div>
          <div 
            class="nav-tab"
            :class="{ active: activeTab === 'favorites' }"
            @click="activeTab = 'favorites'"
          >
            <el-icon class="tab-icon"><Star /></el-icon>
            <span class="tab-text">收藏</span>
          </div>
          <div 
            class="nav-tab"
            :class="{ active: activeTab === 'history' }"
            @click="activeTab = 'history'"
          >
            <el-icon class="tab-icon"><Clock /></el-icon>
            <span class="tab-text">历史记录</span>
            <span class="tab-count">{{ watchHistory.length }}</span>
          </div>
        </div>
        
        <div class="nav-search">
          <div class="search-box">
            <el-icon class="search-icon"><Search /></el-icon>
            <input 
              type="text" 
              placeholder="搜索视频" 
              class="search-input"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="profile-content">
      <div class="content-container">
        <!-- Left Column - Main Content -->
        <div class="content-main">
          <!-- Home Tab -->
          <section v-if="activeTab === 'home'" class="content-section">
            <!-- 投稿栏目 -->
            <div class="home-section">
              <div class="section-header">
                <h3 class="section-title">
                  <el-icon class="title-icon"><VideoCamera /></el-icon>
                  投稿
                </h3>
                <el-button type="primary" link @click="activeTab = 'videos'">
                  查看更多
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
              <div class="video-grid" v-if="homeVideos.length > 0">
                <VideoCard
                  v-for="video in homeVideos"
                  :key="video.id"
                  :video="video"
                  @click="handleVideoClick"
                />
              </div>
              <el-empty v-else description="暂无投稿视频" :image-size="80" />
            </div>

            <!-- 分隔线 -->
            <div class="home-section-divider"></div>

            <!-- 收藏栏目 -->
            <div class="home-section">
              <div class="section-header">
                <h3 class="section-title">
                  <el-icon class="title-icon"><Star /></el-icon>
                  收藏
                </h3>
                <el-button type="primary" link @click="activeTab = 'favorites'">
                  查看更多
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
              <div class="video-grid" v-if="homeCollections.length > 0">
                <VideoCard
                  v-for="video in homeCollections"
                  :key="video.id"
                  :video="video"
                  @click="handleVideoClick"
                />
              </div>
              <el-empty v-else description="暂无收藏视频" :image-size="80" />
            </div>

            <!-- 分隔线 -->
            <div class="home-section-divider"></div>

            <!-- 历史记录栏目 -->
            <div class="home-section">
              <div class="section-header">
                <h3 class="section-title">
                  <el-icon class="title-icon"><Clock /></el-icon>
                  历史记录
                </h3>
                <el-button type="primary" link @click="activeTab = 'history'">
                  查看更多
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
              <div class="video-grid" v-if="homeHistory.length > 0">
                <VideoCard
                  v-for="item in homeHistory"
                  :key="item.video.id"
                  :video="item.video"
                  @click="handleVideoClick"
                />
              </div>
              <el-empty v-else description="暂无观看历史" :image-size="80" />
            </div>
          </section>

          <!-- Videos Tab (我的投稿) -->
          <section v-if="activeTab === 'videos'" class="content-section">
            <div class="section-header">
              <h2 class="section-title">
                <el-icon class="title-icon"><VideoCamera /></el-icon>
                我的投稿
              </h2>
            </div>

            <div class="video-grid" v-if="videos.length > 0">
              <VideoCard
                v-for="video in videos"
                :key="video.id"
                :video="video"
                @click="handleVideoClick"
              />
            </div>
            
            <div v-else class="empty-state">
              <el-icon class="empty-icon" :size="48"><VideoCamera /></el-icon>
              <p class="empty-text">暂无投稿视频</p>
              <el-button type="primary" @click="$router.push('/video-center')">
                去投稿
              </el-button>
            </div>
          </section>

          <!-- Collections Tab (我的收藏) -->
          <section v-if="activeTab === 'favorites'" class="content-section">
            <div class="section-header">
              <h2 class="section-title">
                <el-icon class="title-icon"><Star /></el-icon>
                我的收藏
              </h2>
              <el-button 
                type="primary" 
                :icon="Plus" 
                @click="showCreateFolderDialog = true"
                size="small"
              >
                新建收藏夹
              </el-button>
            </div>

            <!-- 文件夹列表 -->
            <div class="folders-list" v-if="collectionFolders.length > 0 || uncategorizedCount > 0">
              <div 
                v-for="folder in collectionFolders" 
                :key="folder.id"
                class="folder-item"
                :class="{ active: selectedFolderId === folder.id }"
                @click="selectFolder(folder.id)"
              >
                <el-icon class="folder-icon"><Folder /></el-icon>
                <span class="folder-name">{{ folder.name }}</span>
                <span class="folder-count">({{ folder.count }})</span>
              </div>
              
              <!-- 未分类选项 -->
              <div 
                class="folder-item"
                :class="{ active: selectedFolderId === null }"
                @click="selectFolder(null)"
              >
                <el-icon class="folder-icon"><Document /></el-icon>
                <span class="folder-name">未分类</span>
                <span class="folder-count">({{ uncategorizedCount }})</span>
              </div>
            </div>

            <!-- 视频列表 -->
            <div class="video-grid" v-if="collections.length > 0">
              <VideoCard
                v-for="video in collections"
                :key="video.id"
                :video="video"
                @click="handleVideoClick"
              />
            </div>
            
            <div v-else-if="selectedFolderId !== undefined" class="empty-state">
              <el-icon class="empty-icon" :size="48"><Star /></el-icon>
              <p class="empty-text">该收藏夹还没有视频哦</p>
            </div>
          </section>

          <!-- History Tab (历史记录) -->
          <section v-if="activeTab === 'history'" class="content-section">
            <div class="section-header">
              <h2 class="section-title">
                <el-icon class="title-icon"><Clock /></el-icon>
                历史记录
              </h2>
            </div>

            <div class="video-grid history-grid" v-if="watchHistory.length > 0">
              <div 
                v-for="item in watchHistory"
                :key="item.id"
                class="history-item-wrapper"
              >
                <VideoCard
                  :video="item.video as Video"
                  @click="() => handleVideoClick(item.video as Video)"
                />
                <el-button
                  class="delete-history-btn"
                  type="danger"
                  :icon="Delete"
                  circle
                  size="small"
                  @click.stop="handleDeleteHistory(item)"
                  title="删除历史记录"
                />
              </div>
            </div>
            
            <div v-else class="empty-state">
              <el-icon class="empty-icon" :size="48"><Clock /></el-icon>
              <p class="empty-text">还没有观看历史</p>
            </div>
          </section>

        </div>

        <!-- Right Column - Sidebar -->
        <div class="content-sidebar">
          <!-- Achievement Card -->
          <div class="sidebar-card achievement-card">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon class="title-icon"><Trophy /></el-icon>
                个人成就
              </h3>
            </div>
            <div class="card-body">
              <div class="achievement-item">
                <span class="achievement-label">获得点赞</span>
                <span class="achievement-value">{{ formatNumber(userStats.total_likes) }}</span>
              </div>
              <div class="achievement-item">
                <span class="achievement-label">获得播放</span>
                <span class="achievement-value">{{ formatNumber(videos.reduce((sum, v) => sum + (v.view_count || 0), 0)) }}</span>
              </div>
              <div class="achievement-item">
                <span class="achievement-label">获得收藏</span>
                <span class="achievement-value">{{ formatNumber(videos.reduce((sum, v) => sum + (v.collect_count || 0), 0)) }}</span>
              </div>
            </div>
          </div>

          <!-- Announcement Card -->
          <div class="sidebar-card announcement-card">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon class="title-icon"><Bell /></el-icon>
                公告
              </h3>
            </div>
            <div class="card-body">
              <p class="announcement-text">
                欢迎来到我的个人空间！感谢关注~
              </p>
            </div>
          </div>

          <!-- Tags Card -->
          <div class="sidebar-card tags-card" v-if="topTags.length > 0">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon class="title-icon"><PriceTag /></el-icon>
                兴趣标签
              </h3>
            </div>
            <div class="card-body">
              <div class="tags-list">
                <el-tag
                  v-for="tag in topTags"
                  :key="tag"
                  class="tag-item"
                  round
                  @click="handleTagClick(tag)"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </div>

          <!-- Followers Management Card -->
          <div class="sidebar-card followers-card" @click="showFollowersDialog = true">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon class="title-icon"><UserFilled /></el-icon>
                粉丝管理
              </h3>
            </div>
            <div class="card-body">
              <div class="followers-stats">
                <div class="stat-row">
                  <span class="stat-label">我关注的</span>
                  <span class="stat-value">{{ followingList.length }}</span>
                </div>
                <div class="stat-row">
                  <span class="stat-label">我的粉丝</span>
                  <span class="stat-value">{{ followersList.length }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Profile Dialog -->
    <el-dialog
      v-model="editVisible"
      title="编辑资料"
      width="500px"
      destroy-on-close
      class="edit-dialog"
    >
      <div class="edit-dialog-body">
        <AvatarSection
          :avatar="userStore.avatar"
          @file-selected="handleFileSelect"
        />
        <InfoForm
          ref="infoFormRef"
          :user-info="displayUser"
          :submitting="submitting"
          @submit="handleSubmit"
        />
      </div>
    </el-dialog>

    <!-- Avatar Cropper -->
    <AvatarCropper
      v-model="cropperVisible"
      :img-src="selectedImageSrc"
      @confirm="handleCropConfirm"
    />

    <!-- Create Folder Dialog -->
    <el-dialog
      v-model="showCreateFolderDialog"
      title="新建收藏夹"
      width="500px"
      @close="newFolderName = ''; newFolderDescription = ''"
    >
      <el-form label-width="100px">
        <el-form-item label="文件夹名称" required>
          <el-input
            v-model="newFolderName"
            placeholder="请输入文件夹名称"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="文件夹描述">
          <el-input
            v-model="newFolderDescription"
            type="textarea"
            placeholder="请输入文件夹描述（可选）"
            :rows="3"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateFolderDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateFolder">创建</el-button>
      </template>
    </el-dialog>

    <!-- Followers Management Dialog -->
    <el-dialog
      v-model="showFollowersDialog"
      title="粉丝管理"
      width="600px"
      @open="loadFollowers"
    >
      <!-- 标签切换 -->
      <div class="followers-tabs">
        <el-radio-group v-model="followersTab" @change="handleFollowersTabChange">
          <el-radio-button label="following">我关注的</el-radio-button>
          <el-radio-button label="followers">我的粉丝</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 加载状态 -->
      <div v-if="followersLoading" class="loading-state">
        <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
        <p class="loading-text">加载中...</p>
      </div>

      <!-- 我关注的列表 -->
      <div v-else-if="followersTab === 'following'" class="followers-list">
        <div v-if="followingList.length > 0" class="user-list">
          <div 
            v-for="user in followingList"
            :key="user.id"
            class="user-item"
          >
            <div class="user-avatar-wrapper" @click="handleUserClick(user.id)">
              <img 
                :src="user.avatar || '/default-avatar.png'" 
                :alt="user.nickname"
                class="user-avatar-img"
              />
            </div>
            <div class="user-info-wrapper">
              <div class="user-name" @click="handleUserClick(user.id)">{{ user.nickname }}</div>
              <div class="user-username">@{{ user.username }}</div>
              <div class="user-time">关注于 {{ formatDate(user.followed_at) }}</div>
            </div>
            <div class="user-actions">
              <el-button 
                type="danger" 
                size="small"
                @click="handleUnfollow(user.id)"
              >
                取消关注
              </el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-icon class="empty-icon" :size="48"><UserFilled /></el-icon>
          <p class="empty-text">还没有关注任何人</p>
        </div>
      </div>

      <!-- 我的粉丝列表 -->
      <div v-else-if="followersTab === 'followers'" class="followers-list">
        <div v-if="followersList.length > 0" class="user-list">
          <div 
            v-for="user in followersList"
            :key="user.id"
            class="user-item"
          >
            <div class="user-avatar-wrapper" @click="handleUserClick(user.id)">
              <img 
                :src="user.avatar || '/default-avatar.png'" 
                :alt="user.nickname"
                class="user-avatar-img"
              />
            </div>
            <div class="user-info-wrapper">
              <div class="user-name" @click="handleUserClick(user.id)">{{ user.nickname }}</div>
              <div class="user-username">@{{ user.username }}</div>
              <div class="user-time">关注于 {{ formatDate(user.followed_at) }}</div>
            </div>
            <div class="user-actions">
              <el-button 
                type="danger" 
                size="small"
                @click="handleRemoveFollower(user.id)"
              >
                移除粉丝
              </el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-icon class="empty-icon" :size="48"><UserFilled /></el-icon>
          <p class="empty-text">还没有粉丝</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch, computed } from "vue";
import { useRouter } from "vue-router";
import { Edit, HomeFilled, VideoCamera, Star, Clock, Search, Trophy, Bell, PriceTag, Delete, Plus, Folder, Document, ArrowRight, UserFilled, Loading } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useUserStore } from "@/shared/stores/user";
import { useUserActions } from "@/features/user/composables/useUserActions";
import { getMyVideos } from "@/features/video/shared/api/video.api";
import { getMyCollections } from "@/features/video/shared/api/video.api";
import { getUserStats, getWatchHistory, type WatchHistoryItem, getCollectionFolders, createCollectionFolder, type CollectionFolder, getFollowers, followUser, unfollowUser, removeFollower, type FollowUser, getUserTopTags } from "@/features/user/api/user.api";
import type { UserInfo, Video } from "@/shared/types/entity";
import { formatNumber } from "@/shared/utils/formatters";

import AppHeader from "@/shared/components/layout/AppHeader.vue";
import VideoCard from "@/features/video/shared/components/VideoCard.vue";
import AvatarSection from "@/features/user/components/AvatarSection.vue";
import InfoForm from "@/features/user/components/InfoForm.vue";
import AvatarCropper from "@/features/user/components/AvatarCropper.vue";

const router = useRouter();
const userStore = useUserStore();
const { submitting, updateUser, uploadUserAvatar } = useUserActions();

const displayUser = reactive<UserInfo>({} as UserInfo);
const videos = ref<Video[]>([]);
const collections = ref<Video[]>([]);
const watchHistory = ref<WatchHistoryItem[]>([]);
const collectionFolders = ref<CollectionFolder[]>([]);
const uncategorizedCount = ref(0);
const selectedFolderId = ref<number | null | undefined>(undefined);
const showCreateFolderDialog = ref(false);
const newFolderName = ref('');
const newFolderDescription = ref('');
const topTags = ref<string[]>([]); // 用户最常用的标签
const userStats = reactive({
  following_count: 0,
  followers_count: 0,
  total_likes: 0
});
const editVisible = ref(false);
const infoFormRef = ref(null);
const activeTab = ref('home');
const showFollowersDialog = ref(false);
const followersTab = ref('following');
const followersLoading = ref(false);
const followingList = ref<any[]>([]);
const followersList = ref<any[]>([]);

// 主页展示数据（前4个）
const homeVideos = computed(() => videos.value.slice(0, 4));
const homeCollections = computed(() => collections.value.slice(0, 4));
const homeHistory = computed(() => watchHistory.value.slice(0, 4));

// Avatar handling
const cropperVisible = ref(false);
const selectedImageSrc = ref("");

// Initialize
onMounted(async () => {
  await userStore.fetchUserInfo();
  Object.assign(displayUser, userStore.userInfo);
  await loadUserStats();
  await loadMyVideos();
  await loadCollectionFolders();
  await loadMyCollections();
  await loadWatchHistory();
  await loadUserTopTags(); // 加载用户最常用标签
  
  // 监听来自导航栏的标签页切换事件
  window.addEventListener('switch-tab', handleTabSwitch);
  
  // 监听视频点赞/收藏变化事件，实时更新数据
  window.addEventListener('video-like-changed', handleVideoLikeChanged);
  window.addEventListener('video-collect-changed', handleVideoCollectChanged);
});

// Handle tab switch from navigation
const handleTabSwitch = (event: Event) => {
  const customEvent = event as CustomEvent;
  if (customEvent.detail && ['home', 'videos', 'favorites', 'history'].includes(customEvent.detail)) {
    activeTab.value = customEvent.detail;
  }
};

// Handle video like/collect changes
const handleVideoLikeChanged = () => {
  // 重新加载用户统计数据和视频列表
  loadUserStats();
  loadMyVideos();
};

const handleVideoCollectChanged = () => {
  // 重新加载用户统计数据、视频列表和收藏列表
  loadUserStats();
  loadMyVideos();
  loadCollectionFolders();
  loadMyCollections();
};

// Cleanup
onUnmounted(() => {
  window.removeEventListener('switch-tab', handleTabSwitch);
  window.removeEventListener('video-like-changed', handleVideoLikeChanged);
  window.removeEventListener('video-collect-changed', handleVideoCollectChanged);
});

// Load user statistics
const loadUserStats = async () => {
  try {
    const res = await getUserStats();
    if (res.success && res.data) {
      Object.assign(userStats, res.data);
    }
  } catch (error) {
    console.error('加载用户统计数据失败:', error);
  }
};

// Load user's videos
const loadMyVideos = async () => {
  try {
    const res = await getMyVideos({ page: 1, page_size: 100 }); // 加载更多以便主页展示
    if (res.success && res.data?.items) {
      videos.value = res.data.items;
    }
  } catch (error) {
    console.error('加载我的视频失败:', error);
  }
};

// Load collection folders
const loadCollectionFolders = async () => {
  try {
    const res = await getCollectionFolders();
    if (res.success && res.data) {
      collectionFolders.value = res.data.folders || [];
      uncategorizedCount.value = res.data.uncategorized_count || 0;
    }
  } catch (error) {
    console.error('加载收藏文件夹失败:', error);
  }
};

// Select folder
const selectFolder = (folderId: number | null) => {
  selectedFolderId.value = folderId;
  loadMyCollections();
};

// Load user's collections
const loadMyCollections = async () => {
  try {
    const res = await getMyCollections({ 
      page: 1, 
      page_size: selectedFolderId.value === undefined ? 100 : 8, // 主页需要更多数据
      folder_id: selectedFolderId.value === undefined ? undefined : selectedFolderId.value
    });
    if (res.success && res.data?.items) {
      collections.value = res.data.items;
    }
  } catch (error) {
    console.error('加载我的收藏失败:', error);
  }
};

// Create folder
const handleCreateFolder = async () => {
  if (!newFolderName.value.trim()) {
    ElMessage.warning('请输入文件夹名称');
    return;
  }

  try {
    const res = await createCollectionFolder(newFolderName.value.trim(), newFolderDescription.value.trim() || undefined);
    if (res.success && res.data) {
      ElMessage.success('创建成功');
      await loadCollectionFolders();
      showCreateFolderDialog.value = false;
      newFolderName.value = '';
      newFolderDescription.value = '';
    }
  } catch (error: any) {
    console.error('创建文件夹失败:', error);
    ElMessage.error(error.response?.data?.detail || '创建文件夹失败');
  }
};

// Load watch history
const loadWatchHistory = async () => {
  try {
    const res = await getWatchHistory({ page: 1, page_size: 100 }); // 加载更多历史记录
    if (res.success && res.data?.items) {
      watchHistory.value = res.data.items;
    }
  } catch (error) {
    console.error('加载观看历史失败:', error);
  }
};

// Delete watch history
const handleDeleteHistory = async (item: WatchHistoryItem) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这条观看历史吗？此操作不可恢复。',
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    const { deleteWatchHistory } = await import('@/features/user/api/user.api');
    const res = await deleteWatchHistory(item.id);
    if (res.success) {
      ElMessage.success('删除成功');
      // 重新加载历史记录
      await loadWatchHistory();
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除观看历史失败:', error);
      ElMessage.error('删除失败');
    }
  }
};

const handleVideoClick = (v: Video) => router.push(`/videos/${v.id}`);

// Edit profile handlers
const handleFileSelect = (file: File) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    selectedImageSrc.value = e.target?.result as string;
    cropperVisible.value = true;
  };
  reader.readAsDataURL(file);
};

const handleCropConfirm = async (file: File) => {
  const success = await uploadUserAvatar(file);
  if (success) Object.assign(displayUser, userStore.userInfo);
};

const handleSubmit = async (data: { nickname?: string; intro?: string }) => {
  const success = await updateUser(data);
  if (success) {
    Object.assign(displayUser, userStore.userInfo);
    editVisible.value = false;
  }
};

// 粉丝管理相关函数
const loadFollowers = async () => {
  followersLoading.value = true;
  try {
    const res = await getFollowers();
    if (res.success && res.data) {
      followingList.value = res.data.following || [];
      followersList.value = res.data.followers || [];
    }
  } catch (error) {
    console.error('加载关注列表失败:', error);
    ElMessage.error('加载关注列表失败');
  } finally {
    followersLoading.value = false;
  }
};

const handleFollowersTabChange = () => {
  // 标签切换时不需要重新加载，数据已经在 loadFollowers 中加载了
};

const handleUnfollow = async (userId: number) => {
  try {
    await ElMessageBox.confirm(
      '确定要取消关注该用户吗？',
      '取消关注确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    const res = await unfollowUser(userId);
    if (res.success) {
      ElMessage.success('取消关注成功');
      // 重新加载关注列表和统计数据
      await loadFollowers();
      await loadUserStats();
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('取消关注失败:', error);
      ElMessage.error(error.response?.data?.detail || '取消关注失败');
    }
  }
};

const handleRemoveFollower = async (userId: number) => {
  try {
    await ElMessageBox.confirm(
      '确定要移除该粉丝吗？移除后该用户将不再关注你，此操作不可恢复。',
      '移除粉丝确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    const res = await removeFollower(userId);
    if (res.success) {
      ElMessage.success('移除粉丝成功');
      // 重新加载粉丝列表和统计数据
      await loadFollowers();
      await loadUserStats();
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('移除粉丝失败:', error);
      ElMessage.error(error.response?.data?.detail || '移除粉丝失败');
    }
  }
};

const handleUserClick = (userId: number) => {
  // 跳转到用户主页（如果当前用户是自己，则跳转到个人中心）
  if (userId === userStore.userInfo?.id) {
    router.push('/profile');
  } else {
    router.push(`/users/${userId}`);
  }
};

// Load user top tags
const loadUserTopTags = async () => {
  try {
    if (!userStore.userInfo?.id) return;
    const res = await getUserTopTags(userStore.userInfo.id);
    if (res.success && res.data?.top_tags) {
      topTags.value = res.data.top_tags;
    }
  } catch (error) {
    console.error('加载用户最常用标签失败:', error);
  }
};

// Handle tag click
const handleTagClick = (tag: string) => {
  router.push({ path: '/search', query: { keyword: tag, type: 'video', tags: tag } });
};

const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (days === 0) {
    return '今天';
  } else if (days === 1) {
    return '昨天';
  } else if (days < 7) {
    return `${days}天前`;
  } else if (days < 30) {
    const weeks = Math.floor(days / 7);
    return `${weeks}周前`;
  } else if (days < 365) {
    const months = Math.floor(days / 30);
    return `${months}个月前`;
  } else {
    const years = Math.floor(days / 365);
    return `${years}年前`;
  }
};

// 监听粉丝管理对话框打开，加载数据
watch(showFollowersDialog, async (isOpen) => {
  if (isOpen) {
    await loadFollowers();
  }
});
</script>

<style lang="scss" scoped>
.bili-profile-space {
  min-height: 100vh;
  background: var(--bg-global);
}

/* Banner Section */
.profile-banner {
  position: relative;
  height: 280px;
  overflow: hidden;
}

.banner-bg {
  position: absolute;
  inset: 0;
  background: 
    linear-gradient(135deg, #667eea 0%, #764ba2 100%),
    // 使用 CSS 变量或默认背景
    url(var(--profile-bg-url, '/default-profile-bg.jpg'));
  background-size: cover;
  background-position: center;
  filter: blur(0);
}

.banner-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.1) 0%,
    rgba(0, 0, 0, 0.5) 100%
  );
}

.banner-content {
  position: relative;
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--content-padding);
  height: 100%;
  display: flex;
  align-items: flex-end;
  padding-bottom: var(--space-6);
}

/* User Card */
.user-card {
  display: flex;
  align-items: flex-end;
  gap: var(--space-6);
  width: 100%;
}

.avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.user-avatar {
  width: 96px;
  height: 96px;
  border-radius: var(--radius-circle);
  border: 4px solid rgba(255, 255, 255, 0.9);
  object-fit: cover;
  box-shadow: var(--shadow-lg);
  transform: translateY(24px);
  background: var(--bg-white);
}


.user-info {
  flex: 1;
  color: var(--text-white);
  padding-bottom: var(--space-2);
}

.name-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.nickname {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  margin: 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.vip-badge {
  padding: 2px 8px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: #FFD700;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 1px solid #FFD700;
  border-radius: var(--radius-sm);
}

.user-bio {
  font-size: var(--font-size-sm);
  opacity: 0.9;
  margin: 0 0 var(--space-3);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  max-width: 400px;
}

.user-stats {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
}

.stat-label {
  font-size: var(--font-size-xs);
  opacity: 0.8;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: rgba(255, 255, 255, 0.3);
}

.action-buttons {
  flex-shrink: 0;
  padding-bottom: var(--space-2);
}

.edit-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: var(--text-white);
  border-radius: var(--radius-round);
  backdrop-filter: blur(8px);
  transition: all var(--transition-base);

  .btn-icon {
    font-style: normal;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.3);
    border-color: rgba(255, 255, 255, 0.6);
    transform: translateY(-1px);
  }
}

/* Navigation */
.profile-nav {
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: var(--header-height);
  z-index: var(--z-sticky);
}

.nav-container {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--content-padding);
  padding-left: calc(var(--content-padding) + 120px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
}

.nav-tabs {
  display: flex;
  gap: var(--space-1);
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  position: relative;

  .tab-icon {
    font-style: normal;
    font-size: var(--font-size-lg);
  }

  .tab-count {
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
    margin-left: var(--space-1);
  }

  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  &.active {
    color: var(--primary-color);
    font-weight: var(--font-weight-medium);

    &::after {
      content: '';
      position: absolute;
      bottom: -8px;
      left: 50%;
      transform: translateX(-50%);
      width: 24px;
      height: 3px;
      background: var(--primary-color);
      border-radius: var(--radius-round);
    }
  }
}

.nav-search {
  flex-shrink: 0;
}

.search-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  background: var(--bg-gray-1);
  border-radius: var(--radius-round);
  transition: all var(--transition-base);

  &:focus-within {
    background: var(--bg-white);
    box-shadow: 0 0 0 2px var(--primary-light);
  }
}

.search-icon {
  font-style: normal;
  font-size: var(--font-size-sm);
  opacity: 0.5;
}

.search-input {
  width: 120px;
  border: none;
  background: transparent;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  outline: none;

  &::placeholder {
    color: var(--text-tertiary);
  }
}

/* Main Content */
.profile-content {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: var(--space-6) var(--content-padding);
}

.content-container {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-6);
}

/* Main Column */
.content-main {
  min-width: 0;
}

.content-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-card);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;

  .title-icon {
    font-style: normal;
  }
}

.more-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  background: var(--bg-gray-1);
  border: none;
  border-radius: var(--radius-round);
  cursor: pointer;
  transition: all var(--transition-base);

  .arrow {
    transition: transform var(--transition-base);
  }

  &:hover {
    color: var(--primary-color);
    background: var(--primary-light);

    .arrow {
      transform: translateX(2px);
    }
  }
}

.folders-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-light);

  .folder-item {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.2s;
    background: var(--bg-gray-1);
    border: 1px solid var(--border-light);

    &:hover {
      background: var(--bg-gray-2);
      border-color: var(--primary-color);
    }

    &.active {
      background: var(--primary-light);
      border-color: var(--primary-color);
      color: var(--primary-color);

      .folder-icon {
        color: var(--primary-color);
      }
    }

    .folder-icon {
      font-size: 18px;
    }

    .folder-name {
      font-size: var(--font-size-sm);
      font-weight: var(--font-weight-medium);
    }

    .folder-count {
      font-size: var(--font-size-xs);
      color: var(--text-tertiary);
    }
  }
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) 0;
  color: var(--text-tertiary);

  .empty-icon {
    font-size: 48px;
    margin-bottom: var(--space-4);
    opacity: 0.5;
  }

  .empty-text {
    font-size: var(--font-size-base);
    margin: 0 0 var(--space-4);
  }
}

/* Sidebar */
.content-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.sidebar-card {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.card-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-light);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin: 0;

  .title-icon {
    font-style: normal;
  }
}

.card-body {
  padding: var(--space-4);
}

/* Achievement Card */
.achievement-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) 0;

  &:not(:last-child) {
    border-bottom: 1px solid var(--border-light);
  }
}

.achievement-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.achievement-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--primary-color);
}

/* Announcement Card */
.announcement-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: var(--line-height-relaxed);
  margin: 0;
}

/* Tags Card */
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tag-item {
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  background: var(--bg-gray-1);
  border-radius: var(--radius-round);
  cursor: pointer;
  transition: all var(--transition-base);

  &:hover {
    color: var(--primary-color);
    background: var(--primary-light);
  }
}

/* Edit Dialog */
.edit-dialog-body {
  padding: 0 var(--space-4);
}

/* History Item Wrapper */
.history-item-wrapper {
  position: relative;
  
  .delete-history-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 10;
    opacity: 0;
    transition: opacity var(--transition-base);
  }
  
  &:hover .delete-history-btn {
    opacity: 1;
  }
}

.history-grid {
  position: relative;
}

/* Home Section Styles */
.home-section {
  margin-bottom: var(--space-6);
  
  &:last-child {
    margin-bottom: 0;
  }
  
  .section-header {
    margin-bottom: var(--space-4);
  }
  
  .section-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
  }
}

.home-section-divider {
  height: 1px;
  background: var(--border-light);
  margin: var(--space-6) 0;
  position: relative;
  
  &::before,
  &::after {
    content: '';
    position: absolute;
    top: 50%;
    width: 8px;
    height: 8px;
    background: var(--bg-white);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-circle);
    transform: translateY(-50%);
  }
  
  &::before {
    left: -4px;
  }
  
  &::after {
    right: -4px;
  }
}

/* Followers Management Card */
.followers-card {
  cursor: pointer;
  transition: all var(--transition-base);
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
}

.followers-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) 0;
  
  .stat-label {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
  }
  
  .stat-value {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--primary-color);
  }
}

/* Followers Management Dialog */
.followers-tabs {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-light);
}

.followers-list {
  margin-top: var(--space-4);
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.user-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--bg-gray-1);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  
  &:hover {
    background: var(--bg-gray-2);
    box-shadow: var(--shadow-sm);
  }
}

.user-avatar-wrapper {
  flex-shrink: 0;
  cursor: pointer;
  
  .user-avatar-img {
    width: 56px;
    height: 56px;
    border-radius: var(--radius-circle);
    object-fit: cover;
    border: 2px solid var(--border-light);
    transition: all var(--transition-base);
    
    &:hover {
      border-color: var(--primary-color);
      transform: scale(1.05);
    }
  }
}

.user-info-wrapper {
  flex: 1;
  min-width: 0;
  
  .user-name {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-medium);
    color: var(--text-primary);
    margin-bottom: var(--space-1);
    cursor: pointer;
    transition: color var(--transition-base);
    
    &:hover {
      color: var(--primary-color);
    }
  }
  
  .user-username {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-bottom: var(--space-1);
  }
  
  .user-time {
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
  }
}

.user-actions {
  flex-shrink: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) 0;
  color: var(--text-tertiary);
  
  .loading-icon {
    animation: rotate 1s linear infinite;
    margin-bottom: var(--space-4);
  }
  
  .loading-text {
    font-size: var(--font-size-sm);
    margin: 0;
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Responsive */
@media (max-width: 1200px) {
  .content-container {
    grid-template-columns: 1fr 280px;
  }

  .video-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 992px) {
  .content-container {
    grid-template-columns: 1fr;
  }

  .content-sidebar {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
  }

  .video-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 768px) {
  .nav-container {
    padding-left: var(--content-padding);
  }

  .video-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-sidebar {
    grid-template-columns: 1fr;
  }

  .user-card {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .user-avatar {
    transform: translateY(0);
  }

  .user-info {
    padding-bottom: 0;
  }

  .user-bio {
    max-width: none;
  }

  .action-buttons {
    padding-bottom: 0;
  }
}
</style>
