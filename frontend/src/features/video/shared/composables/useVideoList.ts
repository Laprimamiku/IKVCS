import { ref, type Ref } from "vue";
import { ElMessage } from "element-plus";
import { Star, Film, Monitor, Reading } from "@element-plus/icons-vue";
import { getVideoList } from "@/features/video/shared/api/video.api";
import { getCategories } from "@/features/video/shared/api/category.api";
import { resolveFileUrl } from "@/shared/utils/urlHelpers";
import { formatDuration } from "@/shared/utils/formatters";
import type { Video, Category, PageResult } from "@/shared/types/entity";

export interface VideoListItem {
  id: number;
  title: string;
  cover: string;
  duration: string;
  views: number;
  likes: number;
  danmaku: number;
  author: {
    name: string;
    avatar: string;
    verified: boolean;
    verifiedType: string;
  };
  tags: string[];
  publishTime: string;
}

export interface CategoryItem extends Category {
  icon?: any;
}

export function useVideoList() {
  const loading: Ref<boolean> = ref(false);
  const hasMore: Ref<boolean> = ref(true);
  const currentPage: Ref<number> = ref(1);
  const pageSize: Ref<number> = ref(20);
  const videos: Ref<VideoListItem[]> = ref([]);

  const currentCategory: Ref<number | null> = ref(null);
  const categories: Ref<CategoryItem[]> = ref([]);

  const loadCategories = async () => {
    try {
      const response = await getCategories();

      let categoryList: Category[] = [];
      if (response && response.data && Array.isArray(response.data)) {
        categoryList = response.data as Category[];
      } else if (Array.isArray(response)) {
        categoryList = response as Category[];
      }

      if (categoryList && categoryList.length > 0) {
        categories.value = [
          { id: 0, name: "推荐", icon: Star },
          ...categoryList.map((cat) => ({
            ...cat,
            icon: Film,
          })),
        ];
      } else {
        throw new Error("分类列表为空");
      }
    } catch (error) {
      console.error("加载分类失败:", error);
      categories.value = [
        { id: 0, name: "推荐", icon: Star },
        { id: 1, name: "科技", icon: Monitor },
        { id: 2, name: "教育", icon: Reading },
        { id: 3, name: "娱乐", icon: Film },
      ];
    }
  };

  const loadVideos = async (append = false) => {
    if (loading.value) return;
    loading.value = true;

    try {
      const params: {
        page: number;
        page_size: number;
        category_id?: number | null;
      } = {
        page: currentPage.value,
        page_size: pageSize.value,
      };

      if (currentCategory.value) {
        params.category_id = currentCategory.value;
      }

      const response = await getVideoList(params);

      if (response.success) {
        const data = response.data as PageResult<Video>;
        const newVideos: VideoListItem[] = (data.items || []).map((video) => ({
          id: video.id,
          title: video.title,
          cover: resolveFileUrl(video.cover_url),
          duration: formatDuration(video.duration),
          views: video.view_count,
          likes: video.like_count || 0,
          danmaku: video.danmaku_count || 0,
          author: {
            name:
              video.uploader?.nickname ||
              video.uploader?.username ||
              "未知用户",
            avatar: resolveFileUrl(video.uploader?.avatar || ""),
            verified: false,
            verifiedType: "personal",
          },
          tags: [],
          publishTime: video.created_at,
        }));

        if (append) {
          videos.value.push(...newVideos);
        } else {
          videos.value = newVideos;
        }

        hasMore.value = videos.value.length < (data.total || 0);
      }
    } catch (error) {
      console.error("加载视频列表失败:", error);
      ElMessage.error("加载视频列表失败");
    } finally {
      loading.value = false;
    }
  };

  const loadMoreVideos = async () => {
    if (!hasMore.value || loading.value) return;
    currentPage.value++;
    await loadVideos(true);
  };

  const selectCategory = (categoryId: number | null) => {
    currentCategory.value = categoryId;
    currentPage.value = 1;
    loadVideos();
  };

  return {
    loading,
    hasMore,
    currentPage,
    pageSize,
    videos,
    currentCategory,
    categories,
    loadCategories,
    loadVideos,
    loadMoreVideos,
    selectCategory,
  };
}

