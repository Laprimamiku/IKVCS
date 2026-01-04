import { ref, type Ref } from "vue";
import { Star, Film, Monitor, Reading } from "@element-plus/icons-vue";
import { getVideoList } from "@/features/video/shared/api/video.api";
import { getPublicCategories } from "@/features/video/shared/api/category.api";
import { resolveFileUrl } from "@/shared/utils/urlHelpers";
import { formatDuration } from "@/shared/utils/formatters";
import { useListFetch } from "@/shared/composables/useListFetch";
import type { Video, Category } from "@/shared/types/entity";

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
  icon?: string | (() => unknown);
}

export function useVideoList() {
  const currentCategory: Ref<number | null> = ref(null);
  const categories: Ref<CategoryItem[]> = ref([]);

  // 使用通用列表获取 Hook
  const {
    items: videos,
    loading,
    hasMore,
    currentPage,
    pageSize,
    loadData,
    loadMore: loadMoreVideos,
  } = useListFetch<Video>({
    fetchFn: async (params) => {
      const requestParams: {
        page: number;
        page_size: number;
        category_id?: number | null;
      } = {
        page: params.page,
        page_size: params.page_size,
      };

      if (currentCategory.value) {
        requestParams.category_id = currentCategory.value;
      }

      return getVideoList(requestParams);
    },
    transformFn: (video: Video): VideoListItem => ({
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
    }),
    autoLoad: false, // 手动控制加载时机
  });

  const loadCategories = async () => {
    try {
      const response = await getPublicCategories();

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
    await loadData({}, append);
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

